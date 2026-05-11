#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Fetch threads from Hacker News or Reddit and format as markdown or JSON.

This is the main entry point for converting threads from either Hacker News
or Reddit. It auto-detects the source based on the URL or ID provided and
delegates to the appropriate converter (fetch_hn or fetch_reddit modules).

Supports multiple input formats:
- Bare ID with platform hint (e.g., "48072225 hn" or "abc123 reddit")
- Full URLs (auto-detects platform)
- Platform-specific shorthand (r/subreddit/comments/abc123)

Usage:
    fetch-thread.py https://news.ycombinator.com/item?id=48072225
    fetch-thread.py https://reddit.com/r/python/comments/abc123/title
    fetch-thread.py 48072225 hn
    fetch-thread.py abc123 reddit python

Examples:
    fetch-thread.py https://news.ycombinator.com/item?id=48072225
    fetch-thread.py https://reddit.com/r/python/comments/abc123
    fetch-thread.py 48072225 hn --format json | jq .
    fetch-thread.py abc123 reddit python > thread.md
"""

from __future__ import annotations

import argparse
import sys

# Import the converter functions
try:
    from fetch_hn import convert_hn
    from fetch_reddit import convert_reddit
    from _thread_converters import detect_thread_type
except ImportError as e:
    print(f"Error: Could not import converters: {e}", file=sys.stderr)
    print("Make sure fetch-hn.py, fetch-reddit.py, and _thread_converters.py are in the same directory.", file=sys.stderr)
    sys.exit(1)


# ============================================================================
# Source detection and delegation
# ============================================================================

def infer_platform_from_args(args: list[str]) -> tuple[str, list[str]]:
    """Infer the platform (hn or reddit) from command-line arguments.

    Args:
        args: Raw command-line arguments (excluding prog name and flags).

    Returns:
        Tuple of (platform, remaining_args) where platform is 'hn' or 'reddit'.
        If ambiguous, raises ValueError.
    """
    if not args:
        raise ValueError("No source provided")

    first_arg = args[0].lower()

    # Check if first arg is explicit platform hint
    if first_arg in ("hn", "reddit"):
        return first_arg, args

    # Try to detect from content
    detected = detect_thread_type(first_arg)
    if detected != "unknown":
        return detected, args

    # If still unknown and there's a second arg, treat it as a platform hint
    if len(args) > 1:
        second_arg = args[1].lower()
        if second_arg in ("hn", "reddit"):
            return second_arg, args
        # Check if second arg is a subreddit name (for reddit)
        if second_arg not in ("--format", "json", "markdown"):
            return "reddit", args

    raise ValueError(
        f"Could not detect platform from '{first_arg}'. "
        "Please specify explicitly: 'hn' or 'reddit'"
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="fetch-thread",
        description="Fetch threads from Hacker News or Reddit and format as markdown or JSON.",
        epilog=(
            "Examples:\n"
            "  fetch-thread.py https://news.ycombinator.com/item?id=48072225\n"
            "  fetch-thread.py https://reddit.com/r/python/comments/abc123\n"
            "  fetch-thread.py 48072225 hn\n"
            "  fetch-thread.py abc123 reddit python\n"
            "  fetch-thread.py 48072225 --format json | jq .\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "source",
        metavar="SOURCE",
        help="URL, item ID, post ID, or shorthand (auto-detects HN vs Reddit)",
    )
    parser.add_argument(
        "platform_or_subreddit",
        nargs="*",
        metavar="PLATFORM_OR_SUBREDDIT",
        help="Optional: 'hn' or 'reddit', or subreddit name for Reddit posts",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format: markdown (default) or json",
    )
    return parser


def main() -> None:
    """Parse arguments, detect platform, and delegate to the appropriate converter."""
    parser = build_parser()
    args = parser.parse_args()

    # Reconstruct positional arguments in the order they were provided
    positional_args = [args.source] + args.platform_or_subreddit

    try:
        platform, _ = infer_platform_from_args(positional_args)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Reconstruct source argument for the specific converter
    source = " ".join(positional_args).replace("--format", "").strip()

    try:
        if platform == "hn":
            result = convert_hn(source, args.format)
        elif platform == "reddit":
            result = convert_reddit(source, args.format)
        else:
            raise ValueError(f"Unknown platform: {platform}")

        print(result)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
