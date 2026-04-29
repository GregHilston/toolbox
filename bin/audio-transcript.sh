#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Transcribe audio to stdout from a YouTube video or local audio/video file.
# Uses YouTube subtitles when available, falls back to local Parakeet-MLX
# transcription. For local files, video formats are handled by extracting
# audio via ffmpeg first.
#
# Usage:
#   audio-transcript.sh [--start <time>] [--end <time>] [--model <model>] <source>
#
# Sources:
#   YouTube URL    https://www.youtube.com/watch?v=dQw4w9WgXcQ
#   YouTube URL    https://youtu.be/dQw4w9WgXcQ
#   YouTube ID     dQw4w9WgXcQ
#   Local audio    ~/Downloads/audio_message.m4a
#   Local video    ~/Videos/interview.mp4
#   Relative path  ./recording.wav
#
# Time trimming:
#   --start <time>   Start transcription at this timestamp (default: beginning)
#   --end <time>     End transcription at this timestamp (default: end of file)
#
#   Times can be seconds (90), MM:SS (1:30), or HH:MM:SS (0:01:30).
#   You can pass just --start, just --end, or both.
#
#   NOTE: Trimming only applies when audio is transcribed locally via
#   Parakeet-MLX (local files, or YouTube videos without subtitles). If
#   YouTube subtitles are available and used directly, --start/--end are
#   ignored and a warning is printed.
#
# Examples:
#   audio-transcript.sh dQw4w9WgXcQ
#   audio-transcript.sh "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
#   audio-transcript.sh ~/Downloads/voice_memo.m4a
#   audio-transcript.sh --start 1:30 --end 5:00 interview.mp4
#   audio-transcript.sh --start 300 podcast.wav
#   audio-transcript.sh --end 10:00 lecture.mp4
#   audio-transcript.sh --model mlx-community/parakeet-tdt-0.6b-v3 podcast.wav
#   audio-transcript.sh podcast.wav > transcript.txt
#
# To ask Claude (or pi) a question directly, use audio-ask.sh:
#   audio-ask.sh "https://www.youtube.com/watch?v=dQw4w9WgXcQ" "summarize this"
#   audio-ask.sh ~/Downloads/audio_message.m4a "summarize this recording"

# Default Parakeet-MLX model
PARAKEET_MODEL="mlx-community/parakeet-tdt-0.6b-v3"
START_TIME=""
END_TIME=""

if [ $# -eq 0 ]; then
  echo "Usage: audio-transcript [options] <source>"
  echo ""
  echo "Source can be a YouTube URL, YouTube video ID, or path to a local"
  echo "audio/video file."
  echo ""
  echo "Options:"
  echo "  --start <time>   Start at this timestamp (default: beginning)"
  echo "  --end <time>     End at this timestamp (default: end of file)"
  echo "  --model <model>  Parakeet-MLX model (default: parakeet-tdt-0.6b-v3)"
  echo ""
  echo "Time formats: seconds (90), MM:SS (1:30), or HH:MM:SS (0:01:30)"
  echo ""
  echo "  NOTE: --start/--end only apply when transcribing locally via"
  echo "  Parakeet-MLX. If YouTube subtitles are fetched directly, these"
  echo "  flags are ignored (with a warning)."
  echo ""
  echo "Examples:"
  echo "  audio-transcript dQw4w9WgXcQ"
  echo "  audio-transcript 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'"
  echo "  audio-transcript ~/Downloads/voice_memo.m4a"
  echo "  audio-transcript --start 1:30 --end 5:00 interview.mp4"
  echo "  audio-transcript --start 300 podcast.wav"
  echo "  audio-transcript --end 10:00 lecture.mp4"
  echo ""
  echo "Uses Parakeet-MLX for fast, offline transcription on Apple Silicon"
  exit 1
fi

# ---------------------------------------------------------------------------
# Validate a timestamp value. Accepts:
#   - Plain seconds: 90, 0, 3600
#   - MM:SS: 1:30, 01:30
#   - HH:MM:SS: 0:01:30, 1:30:00
# Returns 0 if valid, 1 if invalid.
# ---------------------------------------------------------------------------
validate_timestamp() {
  local ts="$1"
  # Plain seconds (integer or decimal)
  if [[ "$ts" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
    return 0
  fi
  # MM:SS
  if [[ "$ts" =~ ^[0-9]+:[0-5][0-9](\.[0-9]+)?$ ]]; then
    return 0
  fi
  # HH:MM:SS
  if [[ "$ts" =~ ^[0-9]+:[0-5][0-9]:[0-5][0-9](\.[0-9]+)?$ ]]; then
    return 0
  fi
  return 1
}

# Parse all arguments — flags and source can appear in any order
INPUT=""
while [[ $# -gt 0 ]]; do
  case $1 in
  --model | -m)
    PARAKEET_MODEL="$2"
    shift 2
    ;;
  --start)
    START_TIME="$2"
    if ! validate_timestamp "$START_TIME"; then
      echo "Error: Invalid --start time '$START_TIME'. Use seconds (90), MM:SS (1:30), or HH:MM:SS (0:01:30)." >&2
      exit 1
    fi
    shift 2
    ;;
  --end)
    END_TIME="$2"
    if ! validate_timestamp "$END_TIME"; then
      echo "Error: Invalid --end time '$END_TIME'. Use seconds (90), MM:SS (1:30), or HH:MM:SS (0:01:30)." >&2
      exit 1
    fi
    shift 2
    ;;
  -*)
    echo "Unknown option: $1" >&2
    exit 1
    ;;
  *)
    if [[ -n "$INPUT" ]]; then
      echo "Error: Unexpected argument '$1'. Only one source is allowed." >&2
      exit 1
    fi
    INPUT="$1"
    shift
    ;;
  esac
done

if [[ -z "$INPUT" ]]; then
  echo "Error: No source provided. Run 'audio-transcript' with no arguments for usage." >&2
  exit 1
fi

HAS_TIME_FLAGS=false
if [[ -n "$START_TIME" || -n "$END_TIME" ]]; then
  HAS_TIME_FLAGS=true
fi

# ---------------------------------------------------------------------------
# Detect whether input is a YouTube reference or a local file.
#
# YouTube if:
#   - starts with http(s)://
#   - looks like a bare YouTube video ID (11 alphanumeric/dash/underscore chars)
#     AND does not resolve to an existing file on disk
# Otherwise: local file.
# ---------------------------------------------------------------------------
is_youtube() {
  [[ "$1" =~ ^https?:// ]] && return 0
  [[ "$1" =~ ^[a-zA-Z0-9_-]{11}$ ]] && [[ ! -e "$1" ]] && return 0
  return 1
}

# ---------------------------------------------------------------------------
# Build ffmpeg trim flags from START_TIME / END_TIME.
# Sets the global TRIM_ARGS array.
# ---------------------------------------------------------------------------
TRIM_ARGS=()
build_ffmpeg_trim_args() {
  TRIM_ARGS=()
  if [[ -n "$START_TIME" ]]; then
    TRIM_ARGS+=(-ss "$START_TIME")
  fi
  if [[ -n "$END_TIME" ]]; then
    TRIM_ARGS+=(-to "$END_TIME")
  fi
}

# ---------------------------------------------------------------------------
# Parakeet-MLX transcription (shared by YouTube fallback and local files)
# ---------------------------------------------------------------------------
parakeet_transcribe() {
  local audio_file="$1"
  local label="${2:-$(basename "$audio_file")}"

  echo "🦜 Transcribing with Parakeet-MLX ($label)..." >&2
  uv run --with parakeet-mlx python3 <<PYEOF
from parakeet_mlx import from_pretrained
import sys

try:
    model = from_pretrained("$PARAKEET_MODEL")
    result = model.transcribe("$audio_file")
    print(result.text)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
}

# ---------------------------------------------------------------------------
# Trim an audio file if --start/--end were provided.
# Sets AUDIO_FILE to the trimmed file (or leaves it unchanged if no trimming).
# ---------------------------------------------------------------------------
maybe_trim_audio() {
  local input_file="$1"

  if ! $HAS_TIME_FLAGS; then
    AUDIO_FILE="$input_file"
    return
  fi

  if [[ -z "${TEMP_DIR:-}" ]]; then
    TEMP_DIR=$(mktemp -d)
    trap 'rm -rf "$TEMP_DIR"' EXIT
  fi

  local trimmed="$TEMP_DIR/trimmed.wav"
  build_ffmpeg_trim_args

  local range=""
  [[ -n "$START_TIME" ]] && range="from $START_TIME"
  [[ -n "$END_TIME" ]] && range="${range:+$range }to $END_TIME"
  echo "✂️  Trimming audio ($range)..." >&2

  ffmpeg -i "$input_file" ${TRIM_ARGS[@]+"${TRIM_ARGS[@]}"} -vn -acodec pcm_s16le -ar 16000 -ac 1 "$trimmed" -y -loglevel error
  AUDIO_FILE="$trimmed"
}

# ---------------------------------------------------------------------------
# YouTube path
# ---------------------------------------------------------------------------
if is_youtube "$INPUT"; then
  # Extract video ID from various URL formats
  if [[ "$INPUT" =~ ^https?:// ]]; then
    INPUT="${INPUT//\\/}"
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
    VIDEO_ID="$INPUT"
  fi

  # Fetch video metadata via yt-dlp
  echo "Fetching video metadata..." >&2
  set +e
  METADATA_JSON=$(yt-dlp --dump-json --no-warnings "https://www.youtube.com/watch?v=$VIDEO_ID" 2>/dev/null)
  set -e

  if [[ -n "$METADATA_JSON" ]]; then
    METADATA_JSON="$METADATA_JSON" python3 <<'PYEOF'
import json, os

data = json.loads(os.environ['METADATA_JSON'])

date = data.get('upload_date', '')
if len(date) == 8:
    date = f"{date[:4]}-{date[4:6]}-{date[6:]}"

views = data.get('view_count')
views_str = f"{views:,}" if views is not None else 'N/A'

duration = data.get('duration_string') or data.get('duration', 'N/A')
uploader = data.get('uploader') or data.get('channel') or 'N/A'
url = data.get('webpage_url', f"https://www.youtube.com/watch?v={data.get('id','')}")
description = data.get('description', '').strip()

print("=== VIDEO METADATA ===")
print(f"Title:        {data.get('title', 'N/A')}")
print(f"Channel:      {uploader}")
print(f"Upload Date:  {date or 'N/A'}")
print(f"Duration:     {duration}")
print(f"Views:        {views_str}")
print(f"URL:          {url}")
print()
print("Description:")
print(description)
print("=====================")
print()
PYEOF
  fi

  # Try to get existing transcript first
  set +e
  OUTPUT=$(youtube_transcript_api "$VIDEO_ID" 2>&1)
  set -e

  if [[ ! "$OUTPUT" =~ "Could not retrieve a transcript" ]]; then
    if $HAS_TIME_FLAGS; then
      echo "⚠️  Warning: --start/--end flags ignored — transcript was fetched directly from YouTube subtitles." >&2
      echo "   To force local transcription (which respects time trimming), disable subtitles for this video" >&2
      echo "   or use yt-dlp to download the audio and pass the local file instead." >&2
    fi
    echo "=== TRANSCRIPT ==="
    echo "$OUTPUT"
    exit 0
  fi

  # Transcript unavailable — fall back to Parakeet-MLX
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
  echo "No subtitles available for this video." >&2
  echo "Would you like to generate a transcript using Parakeet-MLX?" >&2
  echo "This will download the audio and transcribe it locally." >&2
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
  read -p "Continue? [y/N] " -n 1 -r >&2
  echo >&2

  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled." >&2
    exit 1
  fi

  TEMP_DIR=$(mktemp -d)
  trap 'rm -rf "$TEMP_DIR"' EXIT

  echo "⬇️  Downloading audio..." >&2
  DOWNLOADED="$TEMP_DIR/audio.m4a"
  yt-dlp -f 'bestaudio[ext=m4a]/bestaudio/best' --no-warnings -o "$DOWNLOADED" "https://www.youtube.com/watch?v=$VIDEO_ID" >&2

  maybe_trim_audio "$DOWNLOADED"
  parakeet_transcribe "$AUDIO_FILE" "$VIDEO_ID"
  exit 0
fi

# ---------------------------------------------------------------------------
# Local file path
# ---------------------------------------------------------------------------
INPUT_FILE=$(realpath "$INPUT")

if [[ ! -f "$INPUT_FILE" ]]; then
  echo "Error: File not found: $INPUT_FILE" >&2
  exit 1
fi

# Known audio extensions that Parakeet-MLX can handle directly
AUDIO_EXTS="wav|mp3|m4a|flac|ogg|aac|wma"

EXT="${INPUT_FILE##*.}"
EXT=$(echo "$EXT" | tr '[:upper:]' '[:lower:]')

if [[ "$EXT" =~ ^($AUDIO_EXTS)$ ]]; then
  if $HAS_TIME_FLAGS; then
    # Need to trim — run through ffmpeg even though it's already audio
    maybe_trim_audio "$INPUT_FILE"
  else
    AUDIO_FILE="$INPUT_FILE"
  fi
else
  # Video file — extract audio (and trim if needed) via ffmpeg
  TEMP_DIR=$(mktemp -d)
  trap 'rm -rf "$TEMP_DIR"' EXIT
  AUDIO_FILE="$TEMP_DIR/audio.wav"

  build_ffmpeg_trim_args

  if $HAS_TIME_FLAGS; then
    range=""
    [[ -n "$START_TIME" ]] && range="from $START_TIME"
    [[ -n "$END_TIME" ]] && range="${range:+$range }to $END_TIME"
    echo "Extracting and trimming audio from video ($range)..." >&2
  else
    echo "Extracting audio from video..." >&2
  fi

  ffmpeg -i "$INPUT_FILE" ${TRIM_ARGS[@]+"${TRIM_ARGS[@]}"} -vn -acodec pcm_s16le -ar 16000 -ac 1 "$AUDIO_FILE" -y -loglevel error
fi

parakeet_transcribe "$AUDIO_FILE" "$(basename "$INPUT_FILE")"
