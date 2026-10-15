#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Transcribe an Instagram reel on moria and print its details as JSON.

Reels have no captions to download, so speech-to-text is the only source.
Everything runs on moria in instagram-transcribe-moria.sh, over one ssh call:
Parakeet on its GPU takes seconds, where Whisper on a CPU took ten minutes.
yt-dlp needs no login.

Usage:
    instagram-transcript.py https://www.instagram.com/reel/DecfvksvHiW/
"""

import json
import re
import subprocess
import sys

HOST = "moria"
REMOTE = "~/Git/toolbox/bin/instagram-transcribe-moria.sh"
TIMEOUT = 180


def canonical(url: str) -> str:
    """The reel's bare URL, the only shape moria's side accepts."""
    m = re.search(r"instagram\.com/(reels?|p)/([A-Za-z0-9_-]+)", url)
    if not m:
        sys.exit(f"not an instagram reel or post: {url}")
    kind = "p" if m[1] == "p" else "reel"
    return f"https://www.instagram.com/{kind}/{m[2]}/"


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: instagram-transcript.py <instagram_reel_url>")
    url = canonical(sys.argv[1])
    # BatchMode: a prompt would hang a headless caller.
    cmd = ["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes", HOST, REMOTE, url]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        sys.exit(f"transcribing on {HOST} took over {TIMEOUT} seconds")
    if out.returncode != 0:
        tail = "\n".join(out.stderr.strip().splitlines()[-5:])
        sys.exit(f"failed on {HOST} (exit {out.returncode}). Is it awake and on the tailnet?\n{tail}")
    meta_line, _, transcript = out.stdout.partition("\n")
    meta = json.loads(meta_line)
    date = meta.get("upload_date") or ""
    print(json.dumps({
        "author": meta.get("channel") or meta.get("uploader"),
        "published": f"{date[:4]}-{date[4:6]}-{date[6:]}" if len(date) == 8 else None,
        "caption": meta.get("description") or "",
        "transcript": transcript.strip(),
    }, indent=2))


if __name__ == "__main__":
    main()
