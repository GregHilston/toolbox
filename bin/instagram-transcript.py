#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Transcribe an Instagram reel on moria and print its details as JSON.

Reels have no captions to download, so speech-to-text is the only source.
Everything runs on moria over one ssh call: Parakeet on its GPU takes
seconds, where Whisper on a CPU took ten minutes. yt-dlp needs no login.

Usage:
    instagram-transcript.py https://www.instagram.com/reel/DecfvksvHiW/
"""

import json
import shlex
import subprocess
import sys

HOST = "moria"
MODEL = "mlx-community/parakeet-tdt-0.6b-v3"

REMOTE = """
set -euo pipefail
export PATH=/opt/homebrew/bin:$HOME/.local/bin:$PATH
dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT
cd "$dir"
uvx -q yt-dlp --no-progress -q --no-simulate -x --audio-format mp3 -o 'reel.%(ext)s' \
  -O '%(.{{uploader,channel,upload_date,description}})j' {url}
uvx -q --from parakeet-mlx parakeet-mlx --model {model} --output-format txt reel.mp3 >&2
cat reel.txt
"""


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: instagram-transcript.py <instagram_reel_url>")
    url = sys.argv[1]
    cmd = REMOTE.format(url=shlex.quote(url), model=MODEL)
    try:
        out = subprocess.run(["ssh", HOST, "bash", "-c", shlex.quote(cmd)],
                             capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        sys.exit(f"transcribing on {HOST} took over 10 minutes; is it asleep?")
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
