#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Fetch Hacker News threads and format as markdown or JSON.

Fetches a story or comment from Hacker News via the official HN API
(https://github.com/HackerNews/API) and formats it as markdown or JSON
with comment threading (indented by nesting depth for markdown output).

The HN API is fast and provides clean JSON with no rate limiting for
reasonable usage. This tool recursively fetches kid comments to build
a threaded view (limited to first 10 kids per comment to avoid excessive
API calls).

Usage:
    fetch-hn.py 48072225                       # Markdown (default)
    fetch-hn.py https://news.ycombinator.com/item?id=48072225
    fetch-hn.py 48072225 --format json | jq . # JSON output
    fetch-hn.py 48072225 > thread.md           # Save to file

HTML tags and entities in comment text are stripped for clean output.

Examples:
    fetch-hn.py 48072225
    fetch-hn.py 47999346 | less
    fetch-hn.py "https://news.ycombinator.com/item?id=48072225"
    fetch-hn.py 48072225 --format json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from urllib.error import URLError

from _thread_converters import strip_html_tags


# ============================================================================
# HN API
# ============================================================================

def fetch_item(item_id: int | str) -> dict:
    """Fetch a single HN item (story, comment, poll, etc.) from the API.

    Args:
        item_id: The numeric HN item ID (works with int or str).

    Returns:
        The JSON object from the HN API.

    Raises:
        URLError: If the API request fails (network error, timeout, etc.).
    """
    url = f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read())
    except URLError as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        raise


def extract_item_id(source: str) -> str:
    """Extract the numeric item ID from a URL or bare ID string.

    Args:
        source: Either a bare ID (e.g. '48072225'), a full HN URL
            (e.g. 'https://news.ycombinator.com/item?id=48072225'),
            or a shorthand (e.g. 'news.ycombinator.com/item?id=48072225').

    Returns:
        The numeric item ID as a string.

    Raises:
        ValueError: If no valid item ID can be extracted.
    """
    # Try bare numeric ID
    if re.match(r"^\d+$", source):
        return source

    # Try extracting from HN URLs
    match = re.search(r"id[=?](\d+)", source)
    if match:
        return match.group(1)

    raise ValueError(
        f"Could not extract HN item ID from '{source}'. "
        "Expected a numeric ID or HN URL."
    )


# ============================================================================
# Markdown formatting
# ============================================================================

def format_comment(item: dict, depth: int = 0) -> str:
    """Format an HN comment or story as markdown with nested threading.

    For comments, formats as:
        <indent>**author**:
        <indent>> comment text line 1
        <indent>> comment text line 2
        <blank>
        <nested kids>

    For stories, formats as:
        # Story Title
        **By author** | score points
        <blank>
        story text (if any)
        <nested kids>

    Args:
        item: The HN API item object (story, comment, etc.).
        depth: Nesting depth (0 = root, 1 = direct reply, etc.).
            Used to indent nested comments.

    Returns:
        Formatted markdown string.
    """
    if not item:
        return ""

    indent = "  " * depth
    lines: list[str] = []
    item_type = item.get("type", "unknown")

    if item_type == "comment":
        author = item.get("by", "[deleted]")
        text = strip_html_tags(item.get("text", ""))

        lines.append(f"{indent}**{author}**:")
        for line in text.split("\n"):
            lines.append(f"{indent}> {line}")
        lines.append("")

    elif item_type == "story":
        title = item.get("title", "")
        author = item.get("by", "[deleted]")
        score = item.get("score", 0)
        text = _strip_html_tags(item.get("text", ""))

        lines.append(f"# {title}")
        lines.append(f"**By {author}** | {score} points")
        lines.append("")

        if text:
            lines.append(text)
            lines.append("")

    # Recursively fetch and format kid comments
    kids = item.get("kids", [])
    for kid_id in kids[:10]:  # Limit to first 10 kids to avoid excessive API calls
        try:
            kid = fetch_item(kid_id)
            lines.append(format_comment(kid, depth + 1))
        except URLError:
            # Skip kids that fail to fetch
            pass

    return "\n".join(lines)


# ============================================================================
# High-level converter
# ============================================================================

def convert_hn(source: str, output_format: str = "markdown") -> str:
    """Convert an HN item to markdown or JSON.

    Args:
        source: HN item ID or URL.
        output_format: 'markdown' or 'json'.

    Returns:
        Formatted string (markdown or JSON).

    Raises:
        ValueError: If the source cannot be parsed.
        URLError: If the API request fails.
    """
    try:
        item_id = extract_item_id(source)
    except ValueError as e:
        raise ValueError(f"Invalid HN source: {e}") from e

    item = fetch_item(item_id)

    if output_format == "json":
        return json.dumps(item, indent=2)
    else:
        return format_comment(item)


# ============================================================================
# CLI
# ============================================================================

def build_parser() -> argparse.ArgumentParser:
    """Build the argparse argument parser."""
    parser = argparse.ArgumentParser(
        prog="fetch-hn",
        description="Fetch Hacker News threads and format as markdown or JSON.",
        epilog=(
            "Examples:\n"
            "  fetch-hn.py 48072225\n"
            "  fetch-hn.py https://news.ycombinator.com/item?id=48072225\n"
            "  fetch-hn.py 48072225 --format json | jq .\n"
            "  fetch-hn.py 48072225 > thread.md"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "item",
        metavar="ITEM",
        help="HN item ID or URL (e.g. 48072225 or news.ycombinator.com/item?id=48072225)",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format: markdown (default) or json",
    )
    return parser


def main() -> None:
    """Parse arguments and fetch/format the HN thread."""
    parser = build_parser()
    args = parser.parse_args()

    try:
        result = convert_hn(args.item, args.format)
        print(result)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
