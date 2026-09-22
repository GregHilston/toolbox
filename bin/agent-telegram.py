#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Supervise Hermes runs from a phone, over a Telegram bot.

A run that ends at 3am used to tell nobody until someone opened a laptop, and
`agent-deliver.sh` fixed only half of that: Pushover carries news out and takes
nothing back. The question you actually have at 3am is "is it still moving",
which needs a round trip.

The transport is a long poll to api.telegram.org -- outbound HTTPS, which the
default-deny firewall already permits. No webhook, no inbound port, no public
URL, no firewall change.

`hermes.md` argues the bot belongs on dungeon because a sandboxed agent with
egress could exfiltrate the token. That reasoning does not reach this script:
`agent-sandbox.sh` passes an explicit env allowlist into the container, so a
token in moria's environment never crosses the boundary, and this process runs
on the host outside the sandbox entirely.

Commands are a fixed vocabulary with validated arguments, never a shell. The
allowlist is mandatory -- an unset one refuses to start rather than defaulting
open -- because `/run` spawns work on the box.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

TOOLBOX = Path(os.environ.get("TOOLBOX", Path.home() / "Git/toolbox"))
RUNS = Path.home() / "Git/agent-runs/iter"
LOGS = Path.home() / "Git/agent-runs/logs"
ENV_FILE = Path(os.environ.get("AGENT_NOTIFY_ENV", TOOLBOX / "nixos/secrets/.env"))
CONTAINER = "agent-hermes-vt-smb"

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
API_TIMEOUT = 70  # must exceed the long-poll timeout or every poll raises
POLL_SECONDS = 50
TELEGRAM_LIMIT = 4000


def _load_watcher():
    """`agent-watch.py`'s dash keeps it off the import path; load it by path."""
    spec = importlib.util.spec_from_file_location("agent_watch", TOOLBOX / "bin/agent-watch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_env() -> None:
    """launchd hands an agent none of the shell's environment."""
    if os.environ.get("TELEGRAM_BOT_TOKEN") or not ENV_FILE.is_file():
        return
    for line in ENV_FILE.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class Bot:
    def __init__(self, token: str) -> None:
        # `tests/fake_telegram.py` points this at a local server. The repo's own
        # experience with pi-rpc.py is that this class of script fails in the
        # poll loop rather than in its pure functions, and only a fake transport
        # reaches that. Read per-instance, not as a class attribute, so a test
        # setting the variable after import still wins.
        api = os.environ.get("TELEGRAM_API_BASE", "https://api.telegram.org")
        self.base = f"{api}/bot{token}"

    def api(self, method: str, **params) -> dict:
        data = urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(f"{self.base}/{method}", data=data)
        with urllib.request.urlopen(req, timeout=API_TIMEOUT) as resp:
            return json.loads(resp.read())

    def send(self, chat_id: int, text: str) -> None:
        # No parse_mode: run output is full of paths and underscores, and
        # Telegram rejects the whole message rather than the markup it dislikes.
        try:
            self.api("sendMessage", chat_id=chat_id, text=text[:TELEGRAM_LIMIT] or "(empty)")
        except Exception as exc:
            print(f"send failed: {exc}", file=sys.stderr, flush=True)


def render_run(name: str | None) -> str:
    """Reuse the watcher verbatim -- one renderer, so phone and terminal agree."""
    if name and not NAME_RE.match(name):
        return f"bad run name {name!r}"
    agent_watch = _load_watcher()
    instance = RUNS / name if name else agent_watch.newest_instance()
    if instance is None or not instance.is_dir():
        return f"no such run: {name or '(none found)'}"
    return agent_watch.render(instance)


def list_runs(limit: int = 10) -> str:
    if not RUNS.is_dir():
        return "no runs yet"
    rows = []
    for p in sorted(RUNS.iterdir(), key=lambda q: q.stat().st_mtime, reverse=True)[:limit]:
        db = p / "home/kanban.db"
        status = "?"
        if db.exists():
            try:
                conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2)
                row = conn.execute("select status from tasks order by rowid limit 1").fetchone()
                status = row[0] if row else "?"
                conn.close()
            except Exception:
                pass
        age = (time.time() - p.stat().st_mtime) / 60
        rows.append(f"{p.name:16s} card={status:9s} {age:.0f}m ago")
    return "\n".join(rows) or "no runs yet"


def ensure_docker_on_path() -> None:
    """launchd's PATH has no docker."""
    if shutil.which("docker"):
        return
    for d in ("/usr/local/bin", "/opt/homebrew/bin"):
        if os.access(f"{d}/docker", os.X_OK):
            os.environ["PATH"] = f"{d}:{os.environ.get('PATH', '')}"
            return


def container_running() -> bool:
    out = subprocess.run(
        ["docker", "ps", "--filter", f"name={CONTAINER}", "--format", "{{.Names}}"],
        capture_output=True, text=True,
    )
    return CONTAINER in out.stdout


def start_run(name: str, minutes: int, note: str) -> str:
    if not NAME_RE.match(name):
        return f"bad run name {name!r} — lowercase letters, digits and dashes only"
    if not 1 <= minutes <= 480:
        return f"bad budget {minutes} — must be 1..480 minutes"
    if (RUNS / name).exists():
        return f"{name} already exists — pick another name"
    if container_running():
        return f"{CONTAINER} is already running; /stop it first"

    LOGS.mkdir(parents=True, exist_ok=True)
    logfile = LOGS / f"{name}.log"
    env = {**os.environ, "AGENT_OFFLINE": "1"}
    with logfile.open("wb") as fh:
        subprocess.Popen(
            ["caffeinate", "-dims", str(TOOLBOX / "bin/agent-iterate.sh"),
             name, str(minutes), note or "started from telegram"],
            cwd=TOOLBOX, env=env, stdout=fh, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    return f"started {name} for {minutes}m\nlog: {logfile}\n/status {name} to check"


def tail_log(name: str, lines: int = 25) -> str:
    if not NAME_RE.match(name):
        return f"bad run name {name!r}"
    logfile = LOGS / f"{name}.log"
    if not logfile.is_file():
        return f"no orchestrator log for {name} (only runs started via /run have one)"
    tail = logfile.read_text(errors="ignore").splitlines()[-lines:]
    return "\n".join(tail) or "(log is empty)"


HELP = """hermes harness
/status [name]  board, workspace and model traffic (default: newest run)
/runs           recent runs and their card status
/log [name] [n] tail the orchestrator log
/run <name> <minutes> [note]   start an offline run
/stop           stop the sandbox container
/help           this"""


def handle(text: str) -> str:
    parts = text.strip().split()
    if not parts:
        return HELP
    cmd, args = parts[0].lower().lstrip("/").split("@")[0], parts[1:]

    if cmd in ("help", "start"):
        return HELP
    if cmd == "status":
        return render_run(args[0] if args else None)
    if cmd == "runs":
        return list_runs()
    if cmd == "log":
        name = args[0] if args else None
        if not name:
            return "usage: /log <name> [lines]"
        n = int(args[1]) if len(args) > 1 and args[1].isdigit() else 25
        return tail_log(name, min(n, 100))
    if cmd == "run":
        if len(args) < 2 or not args[1].isdigit():
            return "usage: /run <name> <minutes> [note]"
        return start_run(args[0], int(args[1]), " ".join(args[2:]))
    if cmd == "stop":
        if not container_running():
            return "nothing running"
        subprocess.run(["docker", "stop", CONTAINER], capture_output=True)
        return f"stopped {CONTAINER} — the orchestrator will score and report"
    return f"unknown command {cmd!r}\n\n{HELP}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--once", action="store_true", help="drain, then poll once and exit (for testing)")
    # The offset only reaches the wire on the NEXT poll, so proving it advances
    # takes two. With --once the assertion can only watch the reply instead,
    # which passes with the offset line deleted.
    ap.add_argument("--polls", type=int, default=0, help="exit after N polls (for testing)")
    args = ap.parse_args()

    load_env()
    ensure_docker_on_path()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("TELEGRAM_BOT_TOKEN is not set — see hermes.md 'From your phone'", file=sys.stderr)
        return 78
    raw = os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "").strip()
    if not raw:
        print("TELEGRAM_ALLOWED_CHAT_IDS is not set; refusing to start. This bot can "
              "spawn runs, so it fails closed rather than answering anyone who finds it.",
              file=sys.stderr)
        return 78
    allowed = {int(x) for x in raw.replace(",", " ").split()}

    bot = Bot(token)

    # Drain whatever queued while the bot was down without acting on it: a
    # restart should not replay an hours-old /run.
    offset = None
    discarded = 0
    try:
        while True:
            params = {"timeout": 0}
            if offset is not None:
                params["offset"] = offset
            pending = bot.api("getUpdates", **params).get("result", [])
            if not pending:
                break
            offset = pending[-1]["update_id"] + 1
            discarded += len(pending)
        if discarded:
            print(f"discarded {discarded} stale update(s)", file=sys.stderr, flush=True)
    except Exception as exc:
        print(f"initial drain failed: {exc}", file=sys.stderr, flush=True)

    print(f"listening; allowed chats: {sorted(allowed)}", file=sys.stderr, flush=True)
    polls = 0
    while True:
        try:
            params = {"timeout": POLL_SECONDS}
            if offset is not None:
                params["offset"] = offset
            updates = bot.api("getUpdates", **params).get("result", [])
            polls += 1
        except Exception as exc:
            print(f"poll failed: {exc}", file=sys.stderr, flush=True)
            time.sleep(5)
            continue

        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message") or update.get("edited_message") or {}
            chat_id = (message.get("chat") or {}).get("id")
            text = message.get("text") or ""
            if chat_id is None:
                continue
            if chat_id not in allowed:
                # Silent: do not confirm to a stranger that the bot is alive.
                print(f"ignored chat {chat_id}: {text[:60]!r}", file=sys.stderr, flush=True)
                continue
            print(f"{chat_id}: {text[:120]!r}", file=sys.stderr, flush=True)
            try:
                reply = handle(text)
            except Exception as exc:
                reply = f"command failed: {exc}"
            bot.send(chat_id, reply)

        if args.once or (args.polls and polls >= args.polls):
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
