#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "loguru",
# ]
# ///
"""Ask an AI agent a question about a YouTube video or local audio/video file.

Wraps audio-transcript.py + an agent (claude or pi) into a single command.

Use this script when you want to ask a question about audio without dealing
with the transcript yourself. If you need the raw transcript text -- to save
it, grep it, or pipe it elsewhere -- use audio-transcript.py instead.

Transcript visibility:
    By default, the transcript is NOT printed -- only the agent's response
    and stats are shown. Use --show-transcript to include it in the output.
    (audio-transcript.py always prints the transcript, since that's its
    entire purpose.)

Sources:
    YouTube URL    https://www.youtube.com/watch?v=dQw4w9WgXcQ
    YouTube ID     dQw4w9WgXcQ
    Local audio    ~/Downloads/audio_message.m4a
    Local video    ~/Videos/interview.mp4

Time trimming (--start / --end):
    Passed through to audio-transcript.py. Only applies when transcribing
    locally via Parakeet-MLX. See audio-transcript.py --help for details.

Examples:
    audio-ask.py "https://www.youtube.com/watch?v=bZfr7tzpYqU" "top five guns?"
    audio-ask.py ~/Downloads/audio_message.m4a "summarize this recording"
    audio-ask.py --agent pi interview.mp4 "what are the key points?"
    audio-ask.py --chat --agent pi podcast.m4a "summarize this"
    audio-ask.py --start 1:30 --end 5:00 lecture.mp4 "what was discussed?"
    audio-ask.py --show-transcript lecture.mp4 "what was discussed?"
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from loguru import logger

# Configure loguru: stderr only, no default handler clutter
logger.remove()
logger.add(sys.stderr, format="<level>{level:<8}</level> | {message}", level="DEBUG")

AGENTS = ("claude", "pi")
DEFAULT_AGENT = "claude"


# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------

class _LiveTimer:
    """Context manager that displays a live-updating elapsed timer on stderr.

    When stderr is not a TTY (e.g. captured by a parent process), skips
    intermediate updates and only prints the final elapsed time.
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


def _fmt_duration(seconds: float) -> str:
    """Format a duration as a human-readable string."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"


# ---------------------------------------------------------------------------
# Transcript
# ---------------------------------------------------------------------------

def find_transcript_script() -> str:
    """Locate audio-transcript.py alongside this script."""
    script_dir = Path(__file__).resolve().parent
    candidate = script_dir / "audio-transcript.py"
    if candidate.is_file():
        return str(candidate)
    found = shutil.which("audio-transcript.py")
    if found:
        return found
    raise SystemExit("Error: audio-transcript.py not found alongside this script or on PATH.")


def get_transcript(
    source: str,
    *,
    start: str | None = None,
    end: str | None = None,
    model: str | None = None,
) -> tuple[str, float]:
    """Run audio-transcript.py and return (transcript_text, elapsed_seconds).

    Stderr from the transcript script (progress/stats) is forwarded to our
    stderr in real time.
    """
    cmd = ["uv", "run", find_transcript_script()]
    if start:
        cmd += ["--start", start]
    if end:
        cmd += ["--end", end]
    if model:
        cmd += ["--model", model]
    cmd.append(source)

    t0 = time.monotonic()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.monotonic() - t0

    # Forward stderr (progress/stats) so the user sees them
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    if result.returncode != 0:
        raise SystemExit(f"Transcription failed (exit code {result.returncode}).")
    return result.stdout.strip(), elapsed


# ---------------------------------------------------------------------------
# Agent runners
# ---------------------------------------------------------------------------

def run_oneshot_claude(prompt: str, transcript: str) -> float:
    """Run Claude in one-shot mode. Returns elapsed seconds."""
    t0 = time.monotonic()
    with _LiveTimer("Claude thinking"):
        result = subprocess.run(
            ["claude", "-p", "--output-format", "json", prompt],
            input=transcript, capture_output=True, text=True, check=True,
        )
    elapsed = time.monotonic() - t0

    data = json.loads(result.stdout)
    print(data["result"])
    print()
    print(f"Resume with: claude --resume {data['session_id']}")
    return elapsed


def run_oneshot_pi(prompt: str, transcript: str) -> float:
    """Run pi in one-shot mode. Returns elapsed seconds."""
    t0 = time.monotonic()
    with _LiveTimer("Pi thinking"):
        result = subprocess.run(
            ["pi", "-p", prompt],
            input=transcript, capture_output=True, text=True, check=True,
        )
    elapsed = time.monotonic() - t0

    print(result.stdout.strip())
    print()
    print("Resume with: pi -c")
    return elapsed


def run_chat(agent: str, prompt: str, transcript: str) -> None:
    """Launch the agent in interactive chat mode with the transcript + question."""
    message = f"Transcript: {transcript}\n\nQuestion: {prompt}"
    os.execvp(agent, [agent, message])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="audio-ask",
        description=(
            "Ask an AI agent a question about a YouTube video or local audio/video file.\n\n"
            "By default only the agent's response is printed. The transcript is\n"
            "passed to the agent but not shown. Use --show-transcript to include it."
        ),
        epilog=(
            "time formats: seconds (90), MM:SS (1:30), or HH:MM:SS (0:01:30)\n\n"
            "NOTE: --start/--end are passed through to audio-transcript.py.\n"
            "They only apply when transcribing locally via Parakeet-MLX."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "source",
        help="YouTube URL, YouTube video ID, or path to a local audio/video file",
    )
    parser.add_argument(
        "prompt",
        help="question or instruction for the agent",
    )
    parser.add_argument(
        "--chat",
        action="store_true",
        help="stay in interactive session after the first answer",
    )
    parser.add_argument(
        "--agent",
        choices=AGENTS,
        default=DEFAULT_AGENT,
        help=f"agent to use (default: {DEFAULT_AGENT})",
    )
    parser.add_argument(
        "--show-transcript",
        action="store_true",
        help="print the transcript before the agent's response",
    )
    parser.add_argument(
        "--start",
        metavar="TIME",
        help="start transcription at this timestamp (passed to audio-transcript.py)",
    )
    parser.add_argument(
        "--end",
        metavar="TIME",
        help="end transcription at this timestamp (passed to audio-transcript.py)",
    )
    parser.add_argument(
        "--model",
        metavar="MODEL",
        help="Parakeet-MLX model for local transcription (passed to audio-transcript.py)",
    )
    return parser


def main() -> None:
    overall_t0 = time.monotonic()
    args = build_parser().parse_args()

    transcript, transcript_elapsed = get_transcript(
        args.source, start=args.start, end=args.end, model=args.model,
    )

    if args.show_transcript:
        print(transcript)
        print()

    if args.chat:
        # Chat mode replaces the process — no stats to print
        run_chat(args.agent, args.prompt, transcript)
        return  # unreachable, but makes the type checker happy

    if args.agent == "claude":
        llm_elapsed = run_oneshot_claude(args.prompt, transcript)
    else:
        llm_elapsed = run_oneshot_pi(args.prompt, transcript)

    overall_elapsed = time.monotonic() - overall_t0

    logger.success(
        f"=== ASK STATS ===\n"
        f"  Agent:              {args.agent}\n"
        f"  Transcript length:  {len(transcript):,} chars\n"
        f"  {'Transcription:':<20} {_fmt_duration(transcript_elapsed)}\n"
        f"  {'LLM response:':<20} {_fmt_duration(llm_elapsed)}\n"
        f"  {'Total:':<20} {_fmt_duration(overall_elapsed)}\n"
        f"=================="
    )


if __name__ == "__main__":
    main()
