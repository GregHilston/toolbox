#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "parakeet-mlx",
#     "yt-dlp",
# ]
# ///
#
# Compare Whisper vs Parakeet-MLX transcription on a YouTube video.
# Measures runtime and output quality against YouTube captions.
#
# Usage:
#   ./compare-transcription-models.sh <video-id-or-url>
#   ./compare-transcription-models.sh eIho2S0ZahI
#   ./compare-transcription-models.sh "https://www.youtube.com/watch?v=eIho2S0ZahI"

import subprocess
import tempfile
import os
import sys
import time
import json
from pathlib import Path

# Requires: whisper-ctranslate2 (install via: brew install whisper-ctranslate2)
WHISPER_CMD = "whisper-ctranslate2"


def extract_video_id(input_str: str) -> str:
    """Extract video ID from URL or return as-is if already an ID."""
    if "youtube.com" in input_str or "youtu.be" in input_str:
        # Try to extract from URL using yt-dlp
        try:
            result = subprocess.run(
                ["yt-dlp", "--no-warnings", "-j", input_str],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data.get("id", input_str)
        except Exception:
            pass
    return input_str


def get_youtube_captions(video_id: str) -> str | None:
    """Fetch YouTube captions as ground truth."""
    try:
        result = subprocess.run(
            ["youtube_transcript_api", video_id],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def download_audio(video_id: str, output_path: Path) -> bool:
    """Download audio from YouTube video."""
    try:
        subprocess.run(
            [
                "yt-dlp",
                "-f",
                "bestaudio[ext=m4a]/bestaudio/best",
                "--no-warnings",
                "-o",
                str(output_path),
                f"https://www.youtube.com/watch?v={video_id}",
            ],
            check=True,
            capture_output=True,
            timeout=300,
        )
        return True
    except Exception as e:
        print(f"❌ Failed to download audio: {e}", file=sys.stderr)
        return False


def transcribe_whisper(audio_path: Path, output_dir: Path) -> tuple[float, str | None]:
    """Transcribe with Whisper-ctranslate2, return (time_seconds, text)."""
    print("🎤 Testing Whisper-ctranslate2 (large-v3)...", file=sys.stderr)
    start = time.time()
    try:
        subprocess.run(
            [
                WHISPER_CMD,
                str(audio_path),
                "--model",
                "large-v3",
                "--output_format",
                "txt",
                "--output_dir",
                str(output_dir),
            ],
            check=True,
            capture_output=True,
            timeout=600,
        )
        elapsed = time.time() - start
        txt_file = output_dir / f"{audio_path.stem}.txt"
        if txt_file.exists():
            text = txt_file.read_text().strip()
            return elapsed, text
    except FileNotFoundError:
        print(
            f"❌ {WHISPER_CMD} not found. Install: brew install whisper-ctranslate2",
            file=sys.stderr,
        )
    except subprocess.TimeoutExpired:
        print("❌ Whisper timed out", file=sys.stderr)
    except Exception as e:
        print(f"❌ Whisper error: {e}", file=sys.stderr)
    return 0, None


def transcribe_parakeet(audio_path: Path, output_dir: Path) -> tuple[float, str | None]:
    """Transcribe with Parakeet-MLX, return (time_seconds, text)."""
    print("🦜 Testing Parakeet-MLX (0.6b)...", file=sys.stderr)
    start = time.time()
    try:
        from parakeet_mlx import from_pretrained

        model = from_pretrained("mlx-community/parakeet-tdt-0.6b-v3")
        result = model.transcribe(str(audio_path))
        elapsed = time.time() - start

        return elapsed, result.text
    except ImportError:
        print(
            "❌ parakeet-mlx not installed. Already running via `uv run`?",
            file=sys.stderr,
        )
    except Exception as e:
        print(f"❌ Parakeet error: {e}", file=sys.stderr)
    return 0, None


def compare_texts(text1: str, text2: str, ground_truth: str | None) -> None:
    """Compare two transcriptions and show side-by-side."""

    def text_preview(text: str, max_chars: int = 400) -> str:
        return text[: max_chars - 3] + "..." if len(text) > max_chars else text

    print("\n" + "=" * 80)
    print("WHISPER OUTPUT")
    print("=" * 80)
    print(text_preview(text1))

    print("\n" + "=" * 80)
    print("PARAKEET OUTPUT")
    print("=" * 80)
    print(text_preview(text2))

    if ground_truth:
        print("\n" + "=" * 80)
        print("GROUND TRUTH (YouTube Captions)")
        print("=" * 80)
        print(text_preview(ground_truth))

    # Simple text similarity (word overlap)
    def word_overlap(a: str, b: str) -> float:
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = len(words_a & words_b)
        union = len(words_a | words_b)
        return intersection / union if union > 0 else 0.0

    similarity = word_overlap(text1, text2)
    print(f"\n📊 Word overlap (Whisper vs Parakeet): {similarity:.1%}")

    if ground_truth:
        whisper_vs_gt = word_overlap(text1, ground_truth)
        parakeet_vs_gt = word_overlap(text2, ground_truth)
        print(f"   Whisper vs Ground Truth: {whisper_vs_gt:.1%}")
        print(f"   Parakeet vs Ground Truth: {parakeet_vs_gt:.1%}")


def main():
    if len(sys.argv) < 2:
        print("Usage: compare-transcription-models.sh <video-id-or-url>", file=sys.stderr)
        print("Example: compare-transcription-models.sh eIho2S0ZahI", file=sys.stderr)
        sys.exit(1)

    input_str = sys.argv[1]
    video_id = extract_video_id(input_str)

    print(f"🎬 Video ID: {video_id}", file=sys.stderr)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        audio_file = tmpdir / "audio.m4a"

        # Download audio
        if not download_audio(video_id, audio_file):
            sys.exit(1)

        print(f"✅ Downloaded audio ({audio_file.stat().st_size / 1024 / 1024:.1f} MB)",
              file=sys.stderr)

        # Get ground truth
        print("🎯 Fetching YouTube captions...", file=sys.stderr)
        captions = get_youtube_captions(video_id)
        if captions:
            print("✅ Captions found", file=sys.stderr)
        else:
            print("⚠️  No captions available", file=sys.stderr)

        # Run both models
        whisper_time, whisper_text = transcribe_whisper(audio_file, tmpdir)
        parakeet_time, parakeet_text = transcribe_parakeet(audio_file, tmpdir)

        # Results
        print("\n" + "=" * 80)
        print("TIMING RESULTS")
        print("=" * 80)
        if whisper_time > 0:
            print(f"Whisper:  {whisper_time:.1f}s")
        if parakeet_time > 0:
            print(f"Parakeet: {parakeet_time:.1f}s")
            if whisper_time > 0:
                speedup = whisper_time / parakeet_time
                print(
                    f"Speedup:  {speedup:.2f}x faster"
                    if speedup > 1
                    else f"Slowdown:  {1/speedup:.2f}x slower"
                )

        # Compare transcriptions
        if whisper_text and parakeet_text:
            compare_texts(whisper_text, parakeet_text, captions)
        else:
            print("❌ Could not get transcriptions from both models", file=sys.stderr)


if __name__ == "__main__":
    main()
