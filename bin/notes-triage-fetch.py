#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Fetch a pile of URLs into per-item markdown files for the vault's /triage command.

Sources, combined if several are given:
  --tabs            open tabs from Firefox Sync via ffsclient (needs `ffsclient login` once)
  --client NAME     only tabs from sync clients whose name contains NAME (repeatable)
  --file PATH       one URL per line, or markdown bullets; text after the URL is kept as a note
  URL ...           bare URLs on the command line

Each URL is classified and fetched in parallel:
  youtube        transcript via the youtube-transcript skill (yt-dlp)
  reddit-comment the comment plus its parents and replies, via Reddit's JSON API
  reddit / hn    the thread via fetch-thread.py
  article        Defuddle (same extractor as Obsidian Web Clipper)

Output: a directory of NNN.md files plus index.md. Its path is printed last.

Usage:
    notes-triage-fetch.py --tabs --client Pixel
    notes-triage-fetch.py --file ~/Git/notes/inbox.md
    notes-triage-fetch.py https://news.ycombinator.com/item?id=43753049
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_hn import fetch_item  # noqa: E402
from fetch_reddit import REDDIT_USER_AGENT, load_reddit_cookie  # noqa: E402

YT_SCRIPT = Path.home() / ".claude/skills/youtube-transcript/fetch_transcript.py"
OUT_ROOT = Path.home() / ".cache/notes-triage"

CAP = {"youtube": 7000, "reddit-comment": 3000, "reddit": 4500, "hn": 4500, "article": 3500}
SKIP_PREFIXES = ("about:", "moz-extension:", "chrome:", "file:")
SEARCH_PAGE = re.compile(r"https?://(www\.)?(google\.[a-z.]+/search|duckduckgo\.com/\?|bing\.com/search)")


@dataclass
class Item:
    url: str
    title: str = ""
    note: str = ""
    client: str = ""
    kind: str = ""
    body: str = ""
    error: str = ""
    meta: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- sources


def collect_tabs(clients: list[str]) -> list[Item]:
    out = subprocess.run(
        ["ffsclient", "tabs", "list", "--format", "json", "--ignore-schema-errors"],
        capture_output=True,
        text=True,
    )
    if out.returncode != 0:
        sys.exit(f"ffsclient failed (run `ffsclient login` first?):\n{out.stderr.strip()}")
    items: list[Item] = []
    for rec in json.loads(out.stdout):
        name = rec.get("client_name", "")
        if clients and not any(c.lower() in name.lower() for c in clients):
            continue
        hist = rec.get("urlHistory") or []
        if not hist or hist[0].startswith(SKIP_PREFIXES) or SEARCH_PAGE.match(hist[0]):
            continue
        items.append(Item(url=hist[0], title=rec.get("title", ""), client=name))
    return items


URL_RE = re.compile(r"https?://[^\s<>)\]]+")


def parse_file(path: Path) -> list[Item]:
    items: list[Item] = []
    for line in path.read_text().splitlines():
        m = URL_RE.search(line)
        if not m:
            continue
        note = line[m.end():]
        # drop markdown link closer, then a leading dash/em dash separator
        note = re.sub(r"^\)[^\w]*", "", note.strip()).strip(" -—:")
        items.append(Item(url=m.group(0).rstrip(".,"), note=note))
    return items


# --------------------------------------------------------------------------- classify


def classify(url: str) -> str:
    u = urlparse(url)
    host = u.netloc.lower().removeprefix("www.").removeprefix("old.").removeprefix("m.")
    if host in ("youtube.com", "youtu.be") and (u.path.startswith("/watch") or host == "youtu.be"):
        return "youtube"
    if host == "news.ycombinator.com" and u.path == "/item":
        return "hn"
    if host == "reddit.com" and "/comments/" in u.path:
        parts = [p for p in u.path.split("/") if p]
        # r/<sub>/comments/<post>/<slug>/<comment_id>
        return "reddit-comment" if len(parts) >= 6 else "reddit"
    return "article"


# --------------------------------------------------------------------------- fetchers


def _run(cmd: list[str], timeout: int = 120) -> str:
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip().splitlines()[-1] if out.stderr.strip() else "exit " + str(out.returncode))
    return out.stdout


def fetch_youtube(it: Item) -> None:
    data = json.loads(_run(["python3", str(YT_SCRIPT), it.url], timeout=180))
    it.title = data.get("title") or it.title
    it.body = data.get("transcript", "")


def fetch_thread(it: Item) -> None:
    it.body = _run(["fetch-thread.py", it.url])


def fetch_hn(it: Item) -> None:
    fetch_thread(it)
    item = fetch_item(parse_qs(urlparse(it.url).query)["id"][0])
    for _ in range(12):  # climb from a comment to its story
        if item.get("type") == "story" or "parent" not in item:
            break
        item = fetch_item(item["parent"])
    if item.get("title"):
        it.title = item["title"]
        it.meta = {"story_url": f"https://news.ycombinator.com/item?id={item['id']}"}
        if item.get("url"):
            it.meta["article_url"] = item["url"]


def _reddit_json(url: str) -> object:
    req = urllib.request.Request(url)
    req.add_header("User-Agent", REDDIT_USER_AGENT)
    cookie = load_reddit_cookie()
    if cookie:
        req.add_header("Cookie", cookie)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


def fetch_reddit_comment(it: Item) -> None:
    parts = [p for p in urlparse(it.url).path.split("/") if p]
    sub, post, cid = parts[1], parts[3], parts[5]
    data = _reddit_json(f"https://www.reddit.com/r/{sub}/comments/{post}/_/{cid}.json?context=3")
    p = data[0]["data"]["children"][0]["data"]
    it.title = p.get("title", it.title)
    it.meta = {"subreddit": sub, "post_url": "https://www.reddit.com" + p.get("permalink", "")}
    lines = [f"Post: {p.get('title', '')} (r/{sub}, {p.get('score', 0)} points)"]
    if p.get("selftext"):
        lines.append("> " + p["selftext"][:600].replace("\n", "\n> "))
    lines.append("")

    def walk(listing: dict, depth: int) -> None:
        for ch in listing.get("data", {}).get("children", []):
            if ch.get("kind") != "t1":
                continue
            d = ch["data"]
            marker = " <-- SAVED COMMENT" if d["id"] == cid else ""
            lines.append("  " * depth + f"u/{d.get('author')} ({d.get('score', 0)}){marker}:")
            for ln in d.get("body", "").splitlines():
                lines.append("  " * depth + "  " + ln)
            lines.append("")
            if isinstance(d.get("replies"), dict):
                walk(d["replies"], depth + 1)

    walk(data[1], 0)
    it.body = "\n".join(lines)


def fetch_article(it: Item) -> None:
    raw = _run(["npx", "-y", "defuddle", "parse", it.url, "--markdown", "--json"])
    data = json.loads(raw)
    it.title = data.get("title") or it.title
    it.meta = {k: data.get(k) for k in ("author", "published", "site", "description") if data.get(k)}
    it.body = data.get("content", "")


FETCHERS = {
    "youtube": fetch_youtube,
    "hn": fetch_hn,
    "reddit": fetch_thread,
    "reddit-comment": fetch_reddit_comment,
    "article": fetch_article,
}


def fetch(it: Item) -> Item:
    it.kind = classify(it.url)
    try:
        FETCHERS[it.kind](it)
    except Exception as e:  # noqa: BLE001 — one bad URL must not sink the batch
        it.error = f"{type(e).__name__}: {e}"
    cap = CAP[it.kind]
    if len(it.body) > cap:
        it.body = it.body[:cap].rstrip() + f"\n\n[truncated at {cap} chars]"
    return it


# --------------------------------------------------------------------------- output


def write_bundle(items: list[Item], out: Path) -> None:
    out.mkdir(parents=True)
    rows = ["| # | kind | title | url |", "|---|---|---|---|"]
    for n, it in enumerate(items, 1):
        name = f"{n:03d}"
        flag = " (FETCH FAILED)" if it.error else ""
        rows.append(f"| {name} | {it.kind} | {(it.title or '(no title)')[:70]}{flag} | {it.url} |")
        head = [f"# {name}. {it.title or '(no title)'}", "", f"- url: {it.url}", f"- kind: {it.kind}"]
        if it.client:
            head.append(f"- client: {it.client}")
        if it.note:
            head.append(f"- note: {it.note}")
        for k, v in it.meta.items():
            head.append(f"- {k}: {v}")
        if it.error:
            head.append(f"- error: {it.error}")
        (out / f"{name}.md").write_text("\n".join(head) + "\n\n" + it.body + "\n")
    (out / "index.md").write_text("\n".join(rows) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("urls", nargs="*", metavar="URL")
    ap.add_argument("--tabs", action="store_true", help="read open tabs from Firefox Sync")
    ap.add_argument("--client", action="append", default=[], help="sync client name filter (substring)")
    ap.add_argument("--file", type=Path, help="file of URLs or markdown bullets")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=Path, help="output directory (default: ~/.cache/notes-triage/<timestamp>)")
    args = ap.parse_args()

    items: list[Item] = []
    if args.tabs:
        items += collect_tabs(args.client)
    if args.file:
        items += parse_file(args.file.expanduser())
    items += [Item(url=u) for u in args.urls]

    seen: set[str] = set()
    items = [it for it in items if not (it.url in seen or seen.add(it.url))]
    if not items:
        sys.exit("no URLs to fetch")

    print(f"fetching {len(items)} urls with {args.workers} workers…", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        items = list(pool.map(fetch, items))

    out = args.out or OUT_ROOT / datetime.now().strftime("%Y-%m-%d-%H%M%S")
    write_bundle(items, out)
    failed = sum(1 for it in items if it.error)
    print(f"wrote {len(items)} items ({failed} failed) to:", file=sys.stderr)
    print(out)


if __name__ == "__main__":
    main()
