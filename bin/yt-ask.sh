#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Ask Claude a question about a YouTube video and get an answer.
# Wraps yt-transcript.sh + claude into a single command.
#
# Use this script when you want to ask Claude something about a video without
# dealing with the transcript yourself. If you need the raw transcript text —
# to save it, grep it, or pipe it elsewhere — use yt-transcript.sh instead.
#
# Usage:
#   yt-ask.sh <url-or-id> "<prompt>"           # one-shot: print answer + resume command
#   yt-ask.sh --chat <url-or-id> "<prompt>"    # interactive: stay in chat after first answer
#
# Examples:
#   yt-ask.sh "https://www.youtube.com/watch?v=bZfr7tzpYqU" "what are the top five guns mentioned?"
#   yt-ask.sh --chat dQw4w9WgXcQ "summarize this video"

CHAT_MODE=false

if [[ "${1:-}" == "--chat" ]]; then
  CHAT_MODE=true
  shift
fi

if [[ $# -lt 2 ]]; then
  echo "Usage: yt-ask [--chat] <url-or-id> <prompt>" >&2
  echo "" >&2
  echo "  --chat   Stay in interactive session after the first answer" >&2
  exit 1
fi

URL="$1"
PROMPT="$2"

echo "Fetching transcript..." >&2
TRANSCRIPT=$(yt-transcript.sh "$URL")

if $CHAT_MODE; then
  claude "Transcript: $TRANSCRIPT"$'\n\n'"Question: $PROMPT"
else
  OUT=$(claude -p --output-format json "$PROMPT" <<< "$TRANSCRIPT")
  echo "$OUT" | jq -r '.result'
  echo ""
  echo "Resume with: claude --resume $(echo "$OUT" | jq -r '.session_id')"
fi
