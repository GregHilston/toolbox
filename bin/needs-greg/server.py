#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""One page to see, answer and start every ticket blocked on a person.

Lists open issues with the `needs-greg` label across one owner's repos, parses
the `ask` block at the top of each body, and serves a small page that answers a
ticket (comment plus label removal) or starts a Claude session on it through
Herdr. GitHub calls go through the host's `gh` login, so no token lives here.

Bind stays on 127.0.0.1; publish it with `tailscale serve`. Every request must
carry the `Tailscale-User-Login` header the config allows.

    server.py [--config PATH] [--dry-run]

An `ask` block is a fenced block tagged `ask` in the issue body:

    ask: One line saying what is needed.     (required)
    type: pick | text | done                 (required)
    options: A = first; B = second           (pick only, required there)
    minutes: 2
    images: path/in/repo.jpg, other.png

A value may continue on indented lines. A trailing comment needs two or more
spaces before the `#`, so an issue number inside the ask survives.

Trust: the server believes the Tailscale header and binds 127.0.0.1, so any
local process on the host can call it. That is accepted on a single-user host.

First start in a new checkout: Claude asks once whether to trust the folder.
The start then fails with a message naming the pane; accept the prompt there
and the next start works.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import tomllib
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = Path.home() / ".config" / "needs-greg" / "config.toml"
MODELS = ("haiku", "sonnet", "opus")
TYPES = ("pick", "text", "done")
KEYS = ("ask", "type", "options", "minutes", "images")
LFS_MAGIC = b"version https://git-lfs.github.com/spec/v1"


# ---- ask block -------------------------------------------------------------


class AskError(ValueError):
    pass


@dataclass
class Ask:
    ask: str
    type: str
    options: list[dict] = field(default_factory=list)
    minutes: int | None = None
    images: list[str] = field(default_factory=list)


_FENCE = re.compile(r"\A\s*```ask[ \t]*\n(.*?)^```[ \t]*$", re.S | re.M)
_KEYLINE = re.compile(r"^(" + "|".join(KEYS) + r"):[ \t]*(.*)$")


def _fields(block: str) -> dict[str, str]:
    out: dict[str, str] = {}
    key = None
    for raw in block.splitlines():
        line = re.sub(r"\s{2,}#.*$", "", raw).rstrip()
        m = _KEYLINE.match(line)
        if m:
            key = m.group(1)
            out[key] = m.group(2).strip()
        elif line.strip() and key:
            out[key] = (out[key] + "\n" + line.strip()).strip()
    return out


def _options(text: str) -> list[dict]:
    opts = []
    for part in re.split(r"[;\n]", text):
        part = re.sub(r"^\s*-\s*", "", part).strip()
        if not part:
            continue
        k, sep, label = part.partition("=")
        if not sep or not k.strip():
            raise AskError(f"option needs `KEY = label`: {part!r}")
        opts.append({"key": k.strip(), "label": label.strip()})
    return opts


def parse_ask(body: str | None) -> Ask | None:
    """None when the body has no ask block; AskError when the block is bad."""
    m = _FENCE.search((body or "").replace("\r\n", "\n"))
    if not m:
        return None
    f = _fields(m.group(1))
    if not f.get("ask"):
        raise AskError("ask block needs `ask:`")
    kind = f.get("type", "").split()[:1]
    if not kind or kind[0] not in TYPES:
        raise AskError(f"type must be one of {', '.join(TYPES)}")
    options = _options(f.get("options", ""))
    if kind[0] == "pick" and not options:
        raise AskError("a pick needs `options:`")
    minutes = None
    if f.get("minutes"):
        try:
            minutes = int(f["minutes"].split()[0])
        except ValueError:
            raise AskError(f"minutes must be a number: {f['minutes']!r}") from None
    images = [p.strip() for p in re.split(r"[,;\n]", f.get("images", "")) if p.strip()]
    return Ask(" ".join(f["ask"].split()), kind[0], options, minutes, images)


# ---- config ----------------------------------------------------------------


class ConfigError(ValueError):
    pass


@dataclass
class Config:
    owner: str
    login: str
    session_host: str
    repos: dict[str, str]
    port: int = 8765
    label: str = "needs-greg"
    herdr: str = "herdr"
    gh: str = "gh"


def load_config(path: Path) -> Config:
    try:
        raw = tomllib.loads(Path(path).read_text())
    except FileNotFoundError:
        raise ConfigError(f"no config at {path}; copy config.example.toml there") from None
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"bad TOML in {path}: {e}") from None
    missing = [k for k in ("owner", "login", "session_host") if not raw.get(k)]
    if missing:
        raise ConfigError(f"config is missing: {', '.join(missing)}")
    repos = raw.get("repos")
    if not isinstance(repos, dict) or not repos:
        raise ConfigError("config needs a [repos] table of name = checkout path")
    return Config(
        owner=raw["owner"], login=raw["login"], session_host=raw["session_host"],
        repos={str(k): str(v) for k, v in repos.items()},
        port=int(raw.get("port", 8765)), label=raw.get("label", "needs-greg"),
        herdr=raw.get("herdr", "herdr"), gh=raw.get("gh", "gh"),
    )


def session_is_local(cfg: Config) -> bool:
    return cfg.session_host == "local"


# ---- commands --------------------------------------------------------------


class CommandError(RuntimeError):
    pass


class Runner:
    def __init__(self, cfg: Config, dry_run: bool = False, log=print) -> None:
        self.cfg, self.dry_run, self.log = cfg, dry_run, log
        self.local_session = session_is_local(cfg)

    def _exec(self, argv: list[str], timeout: int = 60, binary: bool = False):
        try:
            p = subprocess.run(argv, capture_output=True, text=not binary, timeout=timeout)
        except FileNotFoundError as e:
            raise CommandError(f"{argv[0]} not found: {e}") from None
        except subprocess.TimeoutExpired:
            raise CommandError(f"timed out after {timeout}s: {argv[0]}") from None
        if p.returncode:
            err = p.stderr if isinstance(p.stderr, str) else p.stderr.decode(errors="replace")
            raise CommandError(err.strip() or f"{argv[0]} exited {p.returncode}")
        return p.stdout

    def gh(self, args: list[str], write: bool = False) -> str:
        if write and self.dry_run:
            self.log("DRY gh " + shlex.join(args))
            return ""
        return self._exec([self.cfg.gh, *args])

    def herdr(self, args: list[str], write: bool = False, timeout: int = 60) -> str:
        inner = [self.cfg.herdr, *args]
        if self.local_session:
            argv = inner
        else:
            argv = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                    self.cfg.session_host, shlex.join(inner)]
        if write and self.dry_run:
            self.log("DRY " + shlex.join(argv))
            return "{}"
        return self._exec(argv, timeout=timeout)


# ---- actions ---------------------------------------------------------------


def _age(created: str, now: datetime | None = None) -> str:
    then = datetime.fromisoformat(created.replace("Z", "+00:00"))
    secs = int(((now or datetime.now(timezone.utc)) - then).total_seconds())
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if secs >= size:
            return f"{secs // size}{unit}"
    return "now"


def list_asks(run: Runner) -> list[dict]:
    cfg = run.cfg
    out = run.gh(["search", "issues", "--owner", cfg.owner, "--label", cfg.label,
                  "--state", "open", "--limit", "200",
                  "--json", "repository,number,title,url,body,createdAt"])
    asks = []
    for it in json.loads(out or "[]"):
        repo = it["repository"]["name"]
        if repo not in cfg.repos:
            continue
        item = {"repo": repo, "number": it["number"], "title": it["title"], "url": it["url"],
                "age": _age(it["createdAt"]), "created": it["createdAt"], "warning": None}
        try:
            a = parse_ask(it.get("body"))
        except AskError as e:
            a, item["warning"] = None, str(e)
        if a is None:
            a = Ask(it["title"], "text")
        item.update(ask=a.ask, type=a.type, options=a.options, minutes=a.minutes, images=a.images)
        asks.append(item)
    asks.sort(key=lambda x: x["created"])
    return asks


def _slug(repo: str, number: int) -> str:
    s = re.sub(r"[^a-z0-9_-]", "-", repo.lower())[:22]
    return f"{s}-{number}" if s[:1].isalpha() else f"r-{s}-{number}"


def _check_repo(cfg: Config, repo: str) -> None:
    if repo not in cfg.repos:
        raise CommandError(f"unknown repo {repo!r}")


def answer(run: Runner, repo: str, number: int, kind: str, text: str = "", note: str = "") -> dict:
    cfg = run.cfg
    _check_repo(cfg, repo)
    text, note = (text or "").strip(), (note or "").strip()
    if kind == "pick":
        if not text:
            raise CommandError("pick needs an option")
        body = f"Decision: {text}" + (f"\n\n{note}" if note else "")
    elif kind == "text":
        if not text:
            raise CommandError("answer is empty")
        body = f"Answer: {text}"
    elif kind == "done":
        body = "Done." + (f"\n\n{note or text}" if note or text else "")
    else:
        raise CommandError(f"unknown kind {kind!r}")
    target = f"{cfg.owner}/{repo}"
    run.gh(["issue", "comment", str(number), "--repo", target, "--body", body], write=True)
    try:
        run.gh(["issue", "edit", str(number), "--repo", target, "--remove-label", cfg.label], write=True)
    except CommandError as e:
        raise CommandError(f"the comment posted, but removing the label {cfg.label} failed: {e}") from None
    return {"ok": True, "comment": body}


def _dig(run: Runner, obj: dict, *keys: str, placeholder: str) -> str:
    """A write's JSON field; only a dry run may fall back to a placeholder."""
    try:
        for k in keys:
            obj = obj[k]
        return obj
    except (KeyError, TypeError):
        if run.dry_run:
            return placeholder
        raise CommandError(f"herdr's reply had no {'.'.join(keys)}") from None


def start(run: Runner, repo: str, number: int, model: str, url: str | None = None) -> dict:
    cfg = run.cfg
    _check_repo(cfg, repo)
    if model not in MODELS:
        raise CommandError(f"model must be one of {', '.join(MODELS)}")
    path, label = cfg.repos[repo], f"#{number}"
    url = url or f"https://github.com/{cfg.owner}/{repo}/issues/{number}"
    name = _slug(repo, number)
    host = "this host" if run.local_session else cfg.session_host
    pane = "?"
    try:
        spaces = json.loads(run.herdr(["workspace", "list"]))["result"]["workspaces"]
        ws = next((w["workspace_id"] for w in spaces if w["label"] == repo), None)
        if ws:
            res = json.loads(run.herdr(["tab", "create", "--workspace", ws, "--cwd", path,
                                        "--label", label, "--no-focus"], write=True) or "{}")
            pane = _dig(run, res, "result", "root_pane", "pane_id", placeholder="<pane>")
        else:
            res = json.loads(run.herdr(["workspace", "create", "--cwd", path, "--label", repo,
                                        "--no-focus"], write=True) or "{}")
            pane = _dig(run, res, "result", "root_pane", "pane_id", placeholder="<pane>")
            tab = _dig(run, res, "result", "tab", "tab_id", placeholder="<tab>")
            run.herdr(["tab", "rename", tab, label], write=True)
        try:
            run.herdr(["agent", "start", name, "--kind", "claude", "--pane", pane,
                       "--", "--model", model], write=True, timeout=90)
        except CommandError as e:
            if "agent_not_ready" in str(e) and "blocked" in str(e):
                raise CommandError(f"Claude in pane {pane} on {host} is waiting on its folder-trust "
                                   "prompt; accept it once, and the next start works") from None
            raise
        run.herdr(["agent", "prompt", name,
                   f"Greg just unblocked #{number} ({url}). Read it with its comments and start on it."],
                  write=True)
    except (CommandError, KeyError, json.JSONDecodeError) as e:
        msg = str(e)
        raise CommandError(msg if "folder-trust" in msg else
                           f"could not start a session on {host}: {msg}") from None
    return {"ok": True, "tab": label, "workspace": repo, "agent": name}


MAX_IMAGE = 15 * 1024 * 1024
IMAGE_TYPES = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
               "gif": "image/gif", "webp": "image/webp"}
_IMAGE_PATH = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_ ./@+-]*\.(" + "|".join(IMAGE_TYPES) + ")", re.I)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _trusted_host(url: str) -> bool:
    u = urlparse(url)
    h = u.hostname or ""
    return u.scheme == "https" and (h == "github.com" or h.endswith(".githubusercontent.com"))


def fetch_image(run: Runner, repo: str, path: str) -> tuple[bytes, str]:
    cfg = run.cfg
    _check_repo(cfg, repo)
    if not _IMAGE_PATH.fullmatch(path) or ".." in path.split("/"):
        raise CommandError("images must be repo-relative png, jpg, gif or webp paths")
    target = f"repos/{cfg.owner}/{repo}/contents/{path}"
    data = run._exec([cfg.gh, "api", "-H", "Accept: application/vnd.github.raw", target], binary=True)
    if data.startswith(LFS_MAGIC):
        meta = json.loads(run.gh(["api", target]))
        url = meta.get("download_url") or ""
        if not _trusted_host(url):
            raise CommandError("image link is not on a GitHub host")
        token = run._exec([cfg.gh, "auth", "token"]).strip()
        req = urllib.request.Request(url, headers={"Authorization": f"token {token}"})
        try:
            with urllib.request.build_opener(_NoRedirect).open(req, timeout=60) as r:
                data = r.read(MAX_IMAGE + 1)
        except OSError as e:
            raise CommandError(f"image download failed: {e}") from None
    if len(data) > MAX_IMAGE:
        raise CommandError("image is over 15 MB")
    return data, IMAGE_TYPES[path.rsplit(".", 1)[1].lower()]


# ---- http ------------------------------------------------------------------


def make_handler(run: Runner):
    cfg = run.cfg

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            run.log("%s %s" % (self.command, self.path))

        def _send(self, status, body: bytes, ctype: str, cache: str = "no-store") -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", cache)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status, obj) -> None:
            self._send(status, json.dumps(obj).encode(), "application/json")

        def _allowed(self) -> bool:
            if self.headers.get("Tailscale-User-Login") != cfg.login:
                self._json(HTTPStatus.FORBIDDEN, {"error": "forbidden"})
                return False
            return True

        def do_GET(self) -> None:
            if not self._allowed():
                return
            u = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            try:
                if u.path == "/":
                    self._send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
                elif u.path == "/api/asks":
                    self._json(200, {"asks": list_asks(run), "repos": sorted(cfg.repos)})
                elif u.path == "/api/image":
                    data, mime = fetch_image(run, q.get("repo", ""), q.get("path", ""))
                    self._send(200, data, mime, "max-age=300")
                else:
                    self._json(404, {"error": "not found"})
            except Exception as e:  # the page must always get a message
                self._json(502, {"error": str(e)})

        def do_POST(self) -> None:
            if not self._allowed():
                return
            origin = self.headers.get("Origin")
            if not origin or urlparse(origin).netloc != self.headers.get("Host"):
                return self._json(403, {"error": "cross-origin"})
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                return self._json(415, {"error": "json only"})
            try:
                n = int(self.headers.get("Content-Length", "0"))
                if not 0 <= n <= 64 * 1024:
                    return self._json(413, {"error": "bad request size"})
                req = json.loads(self.rfile.read(n) or b"{}")
                number = int(req["number"])
                if self.path == "/api/answer":
                    out = answer(run, req["repo"], number, req["kind"], req.get("text", ""),
                                 req.get("note", ""))
                elif self.path == "/api/start":
                    out = start(run, req["repo"], number, req.get("model", "sonnet"))
                else:
                    return self._json(404, {"error": "not found"})
            except (KeyError, ValueError, TypeError) as e:
                return self._json(400, {"error": f"bad request: {e}"})
            except Exception as e:  # the page must always get a message
                return self._json(502, {"error": str(e)})
            self._json(200, out)

    return Handler


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--dry-run", action="store_true", help="log gh and herdr writes, run nothing")
    args = ap.parse_args(argv)
    try:
        cfg = load_config(args.config)
    except ConfigError as e:
        print(f"needs-greg: {e}", file=sys.stderr)
        return 2
    run = Runner(cfg, args.dry_run, log=lambda m: print(m, flush=True))
    where = "local" if run.local_session else f"ssh {cfg.session_host}"
    print(f"needs-greg on 127.0.0.1:{cfg.port}, sessions via {where}"
          + (" (dry run)" if args.dry_run else ""), flush=True)
    ThreadingHTTPServer(("127.0.0.1", cfg.port), make_handler(run)).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
