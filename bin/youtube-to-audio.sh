#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Download audio from a YouTube URL (defaults to m4a, pass --mp3 for mp3)

FORMAT="bestaudio[ext=m4a]"
ARGS=()

for arg in "$@"; do
  if [[ "$arg" == "--mp3" ]]; then
    FORMAT="bestaudio"
  else
    ARGS+=("$arg")
  fi
done

if [[ "$FORMAT" == "bestaudio" ]]; then
  yt-dlp --extract-audio --audio-format mp3 "${ARGS[@]}"
else
  yt-dlp -ci -f "$FORMAT" "${ARGS[@]}"
fi
