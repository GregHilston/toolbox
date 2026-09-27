#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Read a web page as clean markdown: defuddle first, Jina Reader if that fails.

defuddle was the only extractor clean on every server-rendered page tested,
Reddit threads included, but it cannot run JavaScript. Jina Reader (keyless,
about 20 requests a minute) renders it, and bloats and gets blocked more, so it
is only the fallback. JavaScript-only apps such as Bluesky and X defeat both.
Without a defuddle on PATH, npx runs the pinned version.

Usage:
    read-page.py "https://simonwillison.net/2024/Dec/19/one-shot-python-tools/"
    read-page.py "<url>" --max 20000
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import shutil
import subprocess
import sys
import urllib.request
from urllib.error import URLError
from urllib.parse import urlparse

DEFUDDLE_VERSION = "0.19.4"
JINA = "https://r.jina.ai/"
# Less than this is a block page, a cookie wall or an empty JavaScript shell.
MIN_CHARS = 500


def defuddle_cmd() -> list[str] | None:
    if shutil.which("defuddle"):
        return ["defuddle"]
    if shutil.which("npx"):
        return ["npx", "-y", f"defuddle@{DEFUDDLE_VERSION}"]
    return None


def defuddle(url: str) -> tuple[str, str] | None:
    """(title, markdown), or None when defuddle is missing or extracts nothing."""
    cmd = defuddle_cmd()
    if not cmd:
        return None
    try:
        out = subprocess.run([*cmd, "parse", url, "--json"], capture_output=True, text=True, timeout=90)
        page = json.loads(out.stdout) if out.returncode == 0 else {}
    except (subprocess.TimeoutExpired, ValueError):
        return None
    body = (page.get("contentMarkdown") or "").strip()
    return (page.get("title") or "", body) if len(body) >= MIN_CHARS else None


def jina(url: str) -> tuple[str, str] | None:
    req = urllib.request.Request(JINA + url, headers={"X-Return-Format": "markdown"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            text = resp.read().decode("utf-8", "replace")
    except (URLError, TimeoutError):
        return None
    head, sep, body = text.partition("Markdown Content:")
    body = body.strip() if sep else text.strip()
    title = next((line[6:].strip() for line in head.splitlines() if line.startswith("Title:")), "")
    return (title, body) if len(body) >= MIN_CHARS else None


def public(url: str) -> bool:
    """Whether a third party may be sent this URL."""
    host = urlparse(url).hostname or ""
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        return "." in host and not host.endswith((".local", ".internal", ".lan", ".home.arpa"))


def read(url: str) -> tuple[str, str, str]:
    """(title, markdown, extractor). Raises when neither extractor gets real text."""
    # Jina is a third party: lab hosts and their tokens stay here.
    extractors = (("defuddle", defuddle), ("jina", jina)) if public(url) else (("defuddle", defuddle),)
    for name, extract in extractors:
        if got := extract(url):
            return (*got, name)
    raise LookupError(
        "neither defuddle nor Jina Reader got readable text. The page probably needs "
        "JavaScript (Bluesky, X, most web apps), needs a login, or blocks readers."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Read a web page as markdown.")
    parser.add_argument("url")
    parser.add_argument("--max", type=int, default=0, help="cut the text at this many characters (default: all)")
    args = parser.parse_args()
    if not args.url.startswith(("http://", "https://")):
        sys.exit(f"read-page: {args.url!r} is not an http(s) URL")
    try:
        title, body, via = read(args.url)
    except LookupError as e:
        sys.exit(f"read-page: {e}")
    if args.max and len(body) > args.max:
        body = body[: args.max] + f"\n\n[cut at {args.max} of {len(body)} characters]"
    print(f"# {title or args.url}\n\nSource: {args.url} (via {via})\n\n{body}")


if __name__ == "__main__":
    main()
