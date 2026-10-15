#!/usr/bin/env bash
# moria's half of instagram-transcript.py: download a reel's audio, run
# Parakeet on it, and print its metadata as one JSON line, then its transcript.
#
# Hermes' key may run only this (hosts/macs/moria), so sshd passes the
# client's command in SSH_ORIGINAL_COMMAND instead of running it.
# Usage: instagram-transcribe-moria.sh https://www.instagram.com/reel/<id>/
set -euo pipefail
url=${SSH_ORIGINAL_COMMAND:-${1:-}}
url=${url##* }
if [[ ! $url =~ ^https://www\.instagram\.com/(reel|p)/[A-Za-z0-9_-]+/$ ]]; then
  echo "not a canonical instagram reel url: $url" >&2
  exit 2
fi

export PATH=/opt/homebrew/bin:$HOME/.local/bin:$PATH
dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT
cd "$dir"
uvx -q yt-dlp --no-progress -q --no-simulate -x --audio-format mp3 -o 'reel.%(ext)s' \
  -O '%(.{uploader,channel,upload_date,description})j' "$url"
uvx -q --from parakeet-mlx parakeet-mlx --model mlx-community/parakeet-tdt-0.6b-v3 \
  --output-format txt reel.mp3 >&2
cat reel.txt
