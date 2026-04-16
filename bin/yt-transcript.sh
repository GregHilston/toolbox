#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Extract YouTube video transcript, accepting URLs or video IDs
# Falls back to local Whisper transcription if subtitles are unavailable

# Default Whisper model
WHISPER_MODEL="base"

# Parse arguments
if [ $# -eq 0 ]; then
  echo "Usage: yt-transcript <video-id-or-url> [--model <model>]"
  echo "Examples:"
  echo "  yt-transcript dQw4w9WgXcQ"
  echo "  yt-transcript 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'"
  echo "  yt-transcript 'https://youtu.be/dQw4w9WgXcQ'"
  echo "  yt-transcript dQw4w9WgXcQ --model large-v3"
  echo ""
  echo "Available models: tiny, base (default), small, medium, large-v3"
  exit 1
fi

INPUT="$1"
shift

# Parse optional flags
while [[ $# -gt 0 ]]; do
  case $1 in
    --model|-m)
      WHISPER_MODEL="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

# Validate model
case $WHISPER_MODEL in
  tiny|base|small|medium|large-v3)
    ;;
  *)
    echo "Invalid model: $WHISPER_MODEL" >&2
    echo "Available models: tiny, base, small, medium, large-v3" >&2
    exit 1
    ;;
esac

# Extract video ID from various YouTube URL formats
if [[ "$INPUT" =~ ^https?:// ]]; then
  # Remove backslash escapes that zsh might add
  INPUT="${INPUT//\\}"

  # Extract using bash regex (escape special chars)
  if [[ "$INPUT" =~ v=([a-zA-Z0-9_-]+) ]]; then
    VIDEO_ID="${BASH_REMATCH[1]}"
  elif [[ "$INPUT" =~ youtu\.be/([a-zA-Z0-9_-]+) ]]; then
    VIDEO_ID="${BASH_REMATCH[1]}"
  elif [[ "$INPUT" =~ embed/([a-zA-Z0-9_-]+) ]]; then
    VIDEO_ID="${BASH_REMATCH[1]}"
  else
    echo "Error: Could not extract video ID from URL: $INPUT" >&2
    exit 1
  fi
else
  # Already a video ID
  VIDEO_ID="$INPUT"
fi

# Try to get existing transcript first (suppress all output)
# Temporarily disable errexit to capture failure without exiting script
set +e
OUTPUT=$(youtube_transcript_api "$VIDEO_ID" 2>&1)
set -e

# Check if output contains error message (youtube_transcript_api returns 0 even on failure!)
if [[ ! "$OUTPUT" =~ "Could not retrieve a transcript" ]]; then
  # Success - transcript retrieved
  echo "$OUTPUT"
  exit 0
fi

# Transcript unavailable, offer Whisper fallback
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
echo "No subtitles available for this video." >&2
echo "Would you like to generate a transcript using Whisper?" >&2
echo "This will download the audio and transcribe it locally (may take a few minutes)." >&2
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
read -p "Continue? [y/N] " -n 1 -r >&2
echo >&2

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Cancelled." >&2
  exit 1
fi

# Create temp directory for audio
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

echo "⬇️  Downloading audio..." >&2
AUDIO_FILE="$TEMP_DIR/audio.m4a"
# Try multiple format fallbacks to avoid 403 errors
yt-dlp -f 'bestaudio[ext=m4a]/bestaudio/best' --no-warnings -o "$AUDIO_FILE" "https://www.youtube.com/watch?v=$VIDEO_ID" >&2

echo "🎤 Transcribing with Whisper ($WHISPER_MODEL model, this may take a few minutes)..." >&2
whisper-ctranslate2 "$AUDIO_FILE" --model "$WHISPER_MODEL" --output_format txt --output_dir "$TEMP_DIR" >&2

# Output the transcript
cat "$TEMP_DIR/audio.txt"
