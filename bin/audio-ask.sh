#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Ask an AI agent a question about a YouTube video or local audio/video file.
# Wraps audio-transcript.sh + an agent (claude or pi) into a single command.
#
# Use this script when you want to ask a question about audio without dealing
# with the transcript yourself. If you need the raw transcript text — to save
# it, grep it, or pipe it elsewhere — use audio-transcript.sh instead.
#
# Usage:
#   audio-ask.sh [options] <source> "<prompt>"
#
# Options:
#   --chat            Stay in interactive session after the first answer
#   --agent <name>    Agent to use: "claude" (default) or "pi"
#   --start <time>    Start transcription at this timestamp
#   --end <time>      End transcription at this timestamp
#
# Sources:
#   YouTube URL    https://www.youtube.com/watch?v=dQw4w9WgXcQ
#   YouTube ID     dQw4w9WgXcQ
#   Local audio    ~/Downloads/audio_message.m4a
#   Local video    ~/Videos/interview.mp4
#
# Time formats: seconds (90), MM:SS (1:30), or HH:MM:SS (0:01:30)
#   NOTE: --start/--end only apply when transcribing locally via Parakeet-MLX.
#   If YouTube subtitles are fetched directly, these flags are ignored (with
#   a warning). See audio-transcript.sh for details.
#
# Examples:
#   audio-ask.sh "https://www.youtube.com/watch?v=bZfr7tzpYqU" "what are the top five guns?"
#   audio-ask.sh ~/Downloads/audio_message.m4a "summarize this recording"
#   audio-ask.sh --agent pi interview.mp4 "what are the key points?"
#   audio-ask.sh --chat --agent pi podcast.m4a "summarize this"
#   audio-ask.sh --start 1:30 --end 5:00 lecture.mp4 "what was discussed?"

CHAT_MODE=false
AGENT="claude"
TRANSCRIPT_ARGS=()

while [[ $# -gt 0 ]]; do
  case "${1:-}" in
  --chat)
    CHAT_MODE=true
    shift
    ;;
  --agent)
    AGENT="$2"
    shift 2
    ;;
  --start | -s)
    TRANSCRIPT_ARGS+=(--start "$2")
    shift 2
    ;;
  --end | -e)
    TRANSCRIPT_ARGS+=(--end "$2")
    shift 2
    ;;
  --model | -m)
    TRANSCRIPT_ARGS+=(--model "$2")
    shift 2
    ;;
  *)
    break
    ;;
  esac
done

if [[ $# -lt 2 ]]; then
  echo "Usage: audio-ask [options] <source> <prompt>" >&2
  echo "" >&2
  echo "  --chat            Stay in interactive session after the first answer" >&2
  echo "  --agent <name>    Agent to use: claude (default) or pi" >&2
  echo "  --start <time>    Start transcription at this timestamp" >&2
  echo "  --end <time>      End transcription at this timestamp" >&2
  echo "  --model <model>   Parakeet-MLX model for local transcription" >&2
  exit 1
fi

if [[ "$AGENT" != "claude" && "$AGENT" != "pi" ]]; then
  echo "Error: Unknown agent '$AGENT'. Use 'claude' or 'pi'." >&2
  exit 1
fi

SOURCE="$1"
PROMPT="$2"

echo "Fetching transcript..." >&2
TRANSCRIPT=$(audio-transcript.sh ${TRANSCRIPT_ARGS[@]+"${TRANSCRIPT_ARGS[@]}"} "$SOURCE")

if $CHAT_MODE; then
  "$AGENT" "Transcript: $TRANSCRIPT"$'\n\n'"Question: $PROMPT"
else
  if [[ "$AGENT" == "claude" ]]; then
    OUT=$(claude -p --output-format json "$PROMPT" <<< "$TRANSCRIPT")
    echo "$OUT" | jq -r '.result'
    echo ""
    echo "Resume with: claude --resume $(echo "$OUT" | jq -r '.session_id')"
  else
    pi -p "$PROMPT" <<< "$TRANSCRIPT"
    echo ""
    echo "Resume with: pi -c"
  fi
fi
