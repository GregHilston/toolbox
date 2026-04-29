#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "parakeet-mlx",
#     "loguru",
#     "youtube-transcript-api",
# ]
# ///
"""Transcribe audio from a YouTube video or local audio/video file.

Uses YouTube subtitles when available, falls back to local Parakeet-MLX
transcription (optimized for Apple Silicon). For local files, video formats
are handled by extracting audio via ffmpeg first.

Sources:
    YouTube URL    https://www.youtube.com/watch?v=dQw4w9WgXcQ
    YouTube URL    https://youtu.be/dQw4w9WgXcQ
    YouTube ID     dQw4w9WgXcQ
    Local audio    ~/Downloads/audio_message.m4a
    Local video    ~/Videos/interview.mp4
    Relative path  ./recording.wav

Time trimming (--start / --end):
    Only applies when audio is transcribed locally via Parakeet-MLX (local
    files, or YouTube videos without subtitles). If YouTube subtitles are
    available and used directly, --start/--end are ignored and a warning is
    printed.

Examples:
    audio-transcript.py dQw4w9WgXcQ
    audio-transcript.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    audio-transcript.py ~/Downloads/voice_memo.m4a
    audio-transcript.py --start 1:30 --end 5:00 interview.mp4
    audio-transcript.py --start 300 podcast.wav
    audio-transcript.py --end 10:00 lecture.mp4
    audio-transcript.py podcast.wav > transcript.txt

To ask Claude (or pi) a question directly, use audio-ask.py:
    audio-ask.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" "summarize this"
    audio-ask.py --agent pi ~/Downloads/audio_message.m4a "summarize this"
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from loguru import logger
from parakeet_mlx import from_pretrained

# Configure loguru: stderr only, no default handler clutter
logger.remove()
logger.add(sys.stderr, format="<level>{level:<8}</level> | {message}", level="DEBUG")

DEFAULT_MODEL = "mlx-community/parakeet-tdt-0.6b-v3"
AUDIO_EXTENSIONS = {"wav", "mp3", "m4a", "flac", "ogg", "aac", "wma"}
TIMESTAMP_RE = re.compile(
    r"^(?:\d+(?:\.\d+)?|"            # plain seconds: 90, 3.5
    r"\d+:[0-5]\d(?:\.\d+)?|"        # MM:SS: 1:30
    r"\d+:[0-5]\d:[0-5]\d(?:\.\d+)?" # HH:MM:SS: 0:01:30
    r")$"
)
YOUTUBE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{11}$")
YOUTUBE_URL_PATTERNS = [
    re.compile(r"[?&]v=([a-zA-Z0-9_-]+)"),
    re.compile(r"youtu\.be/([a-zA-Z0-9_-]+)"),
    re.compile(r"embed/([a-zA-Z0-9_-]+)"),
]


# ---------------------------------------------------------------------------
# Timing & progress
# ---------------------------------------------------------------------------

class Stats:
    """Collects timing stats for each phase and prints a summary."""

    def __init__(self) -> None:
        self._start = time.monotonic()
        self._phases: list[tuple[str, float]] = []
        self.source_type: str = "unknown"
        self.transcript_method: str = "unknown"
        self.transcript_chars: int = 0

    def record(self, label: str, duration: float) -> None:
        """Record a completed phase."""
        self._phases.append((label, duration))

    def print_summary(self) -> None:
        """Print a timing summary to stderr."""
        total = time.monotonic() - self._start
        phases = "\n".join(
            f"  {label + ':':<20} {_fmt_duration(duration)}"
            for label, duration in self._phases
        )
        logger.success(
            f"=== STATS ===\n"
            f"  Source:             {self.source_type}\n"
            f"  Transcript method:  {self.transcript_method}\n"
            f"  Transcript length:  {self.transcript_chars:,} chars\n"
            f"{phases}\n"
            f"  {'Total:':<20} {_fmt_duration(total)}\n"
            f"=============="
        )


def _fmt_duration(seconds: float) -> str:
    """Format a duration as a human-readable string."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"


class _Timer:
    """Context manager that records its elapsed time into Stats."""

    def __init__(self, stats: Stats, label: str) -> None:
        self._stats = stats
        self._label = label
        self._t0 = 0.0

    def __enter__(self) -> _Timer:
        self._t0 = time.monotonic()
        return self

    def __exit__(self, *_: object) -> None:
        self._stats.record(self._label, time.monotonic() - self._t0)


def timed(stats: Stats, label: str) -> _Timer:
    """Create a context manager that records the duration of a block into stats."""
    return _Timer(stats, label)


class _LiveTimer:
    """Context manager that displays a live-updating elapsed timer on stderr.

    Uses a background thread to refresh the display every 0.25s, so the timer
    keeps ticking even while the main thread is blocked on I/O.

    When stderr is not a TTY (e.g. captured by a parent process), skips
    intermediate updates and only prints the final elapsed time to avoid
    flooding the output with non-overwriting lines.
    """

    def __init__(self, label: str) -> None:
        self._label = label
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._t0 = 0.0
        self._is_tty = sys.stderr.isatty()

    def _run(self) -> None:
        while not self._stop.wait(0.25):
            elapsed = time.monotonic() - self._t0
            m, s = divmod(int(elapsed), 60)
            sys.stderr.write(f"\r{self._label}: {m:02d}:{s:02d}")
            sys.stderr.flush()

    def __enter__(self) -> _LiveTimer:
        self._t0 = time.monotonic()
        if self._is_tty:
            sys.stderr.write(f"\r{self._label}: 00:00")
            sys.stderr.flush()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join()
        elapsed = time.monotonic() - self._t0
        m, s = divmod(int(elapsed), 60)
        if self._is_tty:
            sys.stderr.write(f"\r{self._label}: {m:02d}:{s:02d}\n")
        else:
            sys.stderr.write(f"{self._label}: {m:02d}:{s:02d}\n")
        sys.stderr.flush()


def run_with_progress(
    cmd: list[str],
    label: str,
    *,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess with a live elapsed-time display on stderr."""
    with _LiveTimer(label):
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            stdout=subprocess.PIPE if not capture_output else None,
            stderr=subprocess.PIPE if not capture_output else None,
        )
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd)
    return result


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def validate_timestamp(value: str) -> str:
    """Argparse type validator for timestamp strings."""
    if not TIMESTAMP_RE.match(value):
        raise argparse.ArgumentTypeError(
            f"invalid time '{value}' — use seconds (90), MM:SS (1:30), or HH:MM:SS (0:01:30)"
        )
    return value


def is_youtube(source: str) -> bool:
    """Return True if the source looks like a YouTube URL or video ID."""
    if source.startswith(("http://", "https://")):
        return True
    return bool(YOUTUBE_ID_RE.match(source)) and not Path(source).exists()


def extract_video_id(source: str) -> str:
    """Extract a YouTube video ID from a URL or bare ID string."""
    if not source.startswith(("http://", "https://")):
        return source
    for pattern in YOUTUBE_URL_PATTERNS:
        match = pattern.search(source)
        if match:
            return match.group(1)
    raise SystemExit(f"Error: Could not extract video ID from URL: {source}")


def describe_time_range(start: str | None, end: str | None) -> str:
    """Build a human-readable time range description."""
    parts = []
    if start:
        parts.append(f"from {start}")
    if end:
        parts.append(f"to {end}")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# External tool wrappers
# ---------------------------------------------------------------------------

def fetch_youtube_metadata(video_id: str, stats: Stats) -> None:
    """Print YouTube video metadata to stderr via yt-dlp."""
    with timed(stats, "Metadata fetch"):
        result = run_with_progress(
            ["yt-dlp", "--dump-json", "--no-warnings",
             f"https://www.youtube.com/watch?v={video_id}"],
            "Fetching metadata",
            check=False, capture_output=True,
        )
    if result.returncode != 0 or not result.stdout.strip():
        return

    data = json.loads(result.stdout)
    date_raw = data.get("upload_date", "")
    date = f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:]}" if len(date_raw) == 8 else "N/A"
    views = data.get("view_count")
    views_str = f"{views:,}" if views is not None else "N/A"
    duration = data.get("duration_string") or data.get("duration", "N/A")
    uploader = data.get("uploader") or data.get("channel") or "N/A"
    url = data.get("webpage_url", f"https://www.youtube.com/watch?v={data.get('id', '')}")
    description = data.get("description", "").strip()

    desc_preview = description[:120] + ("..." if len(description) > 120 else "")
    logger.info(
        f"=== VIDEO METADATA ===\n"
        f"  Title:        {data.get('title', 'N/A')}\n"
        f"  Channel:      {uploader}\n"
        f"  Upload Date:  {date}\n"
        f"  Duration:     {duration}\n"
        f"  Views:        {views_str}\n"
        f"  URL:          {url}\n"
        f"  Description:  {desc_preview}\n"
        f"====================="
    )


def fetch_youtube_subtitles(video_id: str, stats: Stats) -> str | None:
    """Try to fetch existing YouTube subtitles. Return text or None."""
    with timed(stats, "Subtitle fetch"):
        result = run_with_progress(
            ["youtube_transcript_api", video_id],
            "Fetching subtitles",
            check=False, capture_output=True,
        )
    if "Could not retrieve a transcript" in (result.stdout or ""):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def download_youtube_audio(video_id: str, output_path: Path, stats: Stats) -> None:
    """Download audio from a YouTube video via yt-dlp."""
    with timed(stats, "Audio download"):
        run_with_progress(
            ["yt-dlp", "-f", "bestaudio[ext=m4a]/bestaudio/best", "--no-warnings",
             "-o", str(output_path),
             f"https://www.youtube.com/watch?v={video_id}"],
            "Downloading audio",
        )


def ffmpeg_extract_audio(
    input_path: Path,
    output_path: Path,
    stats: Stats,
    *,
    start: str | None = None,
    end: str | None = None,
) -> None:
    """Extract (and optionally trim) audio from a file via ffmpeg."""
    cmd: list[str] = ["ffmpeg", "-i", str(input_path)]
    if start:
        cmd += ["-ss", start]
    if end:
        cmd += ["-to", end]
    cmd += ["-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            str(output_path), "-y", "-loglevel", "error"]

    label = "Extracting audio"
    if start or end:
        label = f"Trimming audio ({describe_time_range(start, end)})"

    with timed(stats, "Audio extraction"):
        run_with_progress(cmd, label)


def parakeet_transcribe(audio_path: Path, model_name: str, label: str, stats: Stats) -> str:
    """Transcribe an audio file using Parakeet-MLX. Returns the transcript text."""
    with timed(stats, "Transcription"), _LiveTimer(f"Transcribing ({label})"):
        model = from_pretrained(model_name)
        result = model.transcribe(str(audio_path))
    stats.transcript_method = f"Parakeet-MLX ({model_name.split('/')[-1]})"
    return result.text


# ---------------------------------------------------------------------------
# High-level transcription flows
# ---------------------------------------------------------------------------

def transcribe_youtube(
    source: str,
    *,
    model: str,
    start: str | None,
    end: str | None,
    stats: Stats,
) -> str:
    """Transcribe a YouTube video, returning the transcript text."""
    video_id = extract_video_id(source)
    has_time_flags = start is not None or end is not None
    stats.source_type = f"YouTube ({video_id})"

    fetch_youtube_metadata(video_id, stats)

    subtitles = fetch_youtube_subtitles(video_id, stats)
    if subtitles is not None:
        stats.transcript_method = "YouTube subtitles (downloaded)"
        if has_time_flags:
            logger.warning(
                "--start/--end flags ignored — transcript was fetched "
                "directly from YouTube subtitles. To force local transcription "
                "(which respects time trimming), use yt-dlp to download the "
                "audio and pass the local file instead."
            )
        return f"=== TRANSCRIPT ===\n{subtitles}"

    logger.warning("No subtitles available — falling back to local Parakeet-MLX transcription")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        downloaded = tmp_path / "audio.m4a"
        download_youtube_audio(video_id, downloaded, stats)

        if has_time_flags:
            ffmpeg_extract_audio(downloaded, tmp_path / "trimmed.wav", stats,
                                 start=start, end=end)
            audio_path = tmp_path / "trimmed.wav"
        else:
            audio_path = downloaded

        return parakeet_transcribe(audio_path, model, video_id, stats)


def transcribe_local(
    source: str,
    *,
    model: str,
    start: str | None,
    end: str | None,
    stats: Stats,
) -> str:
    """Transcribe a local audio or video file, returning the transcript text."""
    input_file = Path(source).expanduser().resolve()
    if not input_file.is_file():
        raise SystemExit(f"Error: File not found: {input_file}")

    stats.source_type = f"Local file ({input_file.name})"
    has_time_flags = start is not None or end is not None
    ext = input_file.suffix.lstrip(".").lower()
    is_audio = ext in AUDIO_EXTENSIONS

    if is_audio and not has_time_flags:
        return parakeet_transcribe(input_file, model, input_file.name, stats)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        if is_audio and has_time_flags:
            audio_path = tmp_path / "trimmed.wav"
            ffmpeg_extract_audio(input_file, audio_path, stats, start=start, end=end)
        elif not is_audio:
            audio_path = tmp_path / "audio.wav"
            ffmpeg_extract_audio(input_file, audio_path, stats, start=start, end=end)
        else:
            audio_path = input_file

        return parakeet_transcribe(audio_path, model, input_file.name, stats)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="audio-transcript",
        description="Transcribe audio from a YouTube video or local audio/video file.",
        epilog=(
            "time formats: seconds (90), MM:SS (1:30), or HH:MM:SS (0:01:30)\n\n"
            "NOTE: --start/--end only apply when transcribing locally via\n"
            "Parakeet-MLX. If YouTube subtitles are fetched directly, these\n"
            "flags are ignored (with a warning)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "source",
        help="YouTube URL, YouTube video ID, or path to a local audio/video file",
    )
    parser.add_argument(
        "--start",
        type=validate_timestamp,
        metavar="TIME",
        help="start transcription at this timestamp (default: beginning)",
    )
    parser.add_argument(
        "--end",
        type=validate_timestamp,
        metavar="TIME",
        help="end transcription at this timestamp (default: end of file)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        metavar="MODEL",
        help=f"Parakeet-MLX model (default: {DEFAULT_MODEL})",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    stats = Stats()

    if is_youtube(args.source):
        transcript = transcribe_youtube(
            args.source, model=args.model, start=args.start, end=args.end,
            stats=stats,
        )
    else:
        transcript = transcribe_local(
            args.source, model=args.model, start=args.start, end=args.end,
            stats=stats,
        )

    stats.transcript_chars = len(transcript)
    print(transcript)
    stats.print_summary()


if __name__ == "__main__":
    main()
