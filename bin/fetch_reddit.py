#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Fetch Reddit threads and format as markdown or JSON.

Fetches a Reddit thread (post + comments) via the official Reddit JSON API
and formats it as markdown or JSON with comment threading (indented by nesting
depth for markdown output).

The Reddit JSON endpoint requires a User-Agent header, which is automatically
provided. Comments are nested by depth (indented based on reply nesting).

Usage:
    fetch-reddit.py r/python/comments/abc123/title
    fetch-reddit.py https://reddit.com/r/python/comments/abc123/title
    fetch-reddit.py https://old.reddit.com/r/python/comments/abc123/title
    fetch-reddit.py abc123 python              # post_id subreddit

Examples:
    fetch-reddit.py abc123 python
    fetch-reddit.py r/python/comments/abc123 > thread.md
    fetch-reddit.py abc123 python --format json | jq .
    fetch-reddit.py https://reddit.com/r/python/comments/abc123/title
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from urllib.error import URLError
from urllib.parse import urljoin

from _thread_converters import strip_html_tags


# ============================================================================
# Reddit API
# ============================================================================

REDDIT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)


def fetch_thread(post_id: str, subreddit: str) -> tuple[dict, dict]:
    """Fetch a Reddit thread (post + comments) from the API.

    Args:
        post_id: The post ID (without 't3_' prefix).
        subreddit: The subreddit name (without '/r/' prefix).

    Returns:
        Tuple of (post_data, comments_data) dictionaries.

    Raises:
        URLError: If the API request fails.
        ValueError: If the response cannot be parsed.
    """
    url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json"

    req = urllib.request.Request(url)
    req.add_header("User-Agent", REDDIT_USER_AGENT)

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
    except URLError as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        raise

    if not isinstance(data, list) or len(data) < 2:
        raise ValueError("Unexpected Reddit API response format")

    post = data[0]["data"]["children"][0]["data"]
    comments_listing = data[1]["data"]

    return post, comments_listing


def extract_reddit_info(source: str) -> tuple[str, str]:
    """Extract post ID and subreddit from a URL or shorthand.

    Args:
        source: URL like 'https://reddit.com/r/python/comments/abc123/title',
            or shorthand like 'r/python/comments/abc123' or 'abc123 python'.

    Returns:
        Tuple of (post_id, subreddit).

    Raises:
        ValueError: If the source cannot be parsed.
    """
    # Try: "abc123 python" format
    if " " in source:
        parts = source.split()
        if len(parts) == 2:
            return parts[0], parts[1]

    # Try: URL format
    match = re.search(r"/r/(\w+)/comments/(\w+)", source)
    if match:
        return match.group(2), match.group(1)

    raise ValueError(
        "Could not parse Reddit source. Expected:\n"
        "  - URL: https://reddit.com/r/python/comments/abc123/title\n"
        "  - Shorthand: r/python/comments/abc123\n"
        "  - Post ID + sub: abc123 python"
    )


# ============================================================================
# Comment tree processing
# ============================================================================

def flatten_comments(
    listing: dict,
    depth: int = 0,
    max_comments: int = 100,
    collected: list | None = None,
) -> list[tuple[dict, int]]:
    """Flatten Reddit's nested comment tree into a list with depth info.

    Args:
        listing: The Reddit listing object (from API response).
        depth: Current nesting depth.
        max_comments: Maximum comments to collect (to avoid excessive fetching).
        collected: Accumulator list (internal use).

    Returns:
        List of (comment_data, depth) tuples.
    """
    if collected is None:
        collected = []

    if len(collected) >= max_comments:
        return collected

    children = listing.get("children", [])
    for child in children:
        if len(collected) >= max_comments:
            break

        kind = child.get("kind")
        data = child.get("data", {})

        if kind == "t1":  # Comment
            collected.append((data, depth))

            # Recursively process replies
            if "replies" in data and isinstance(data["replies"], dict):
                flatten_comments(data["replies"].get("data", {}), depth + 1, max_comments, collected)
        elif kind == "more":
            # "Load more comments" node — skip for simplicity
            pass

    return collected


# ============================================================================
# Markdown formatting
# ============================================================================

def format_post(post: dict) -> str:
    """Format a Reddit post as markdown.

    Args:
        post: The post data dict from the Reddit API.

    Returns:
        Formatted markdown string.
    """
    title = post.get("title", "")
    author = post.get("author", "[deleted]")
    score = post.get("score", 0)
    text = strip_html_tags(post.get("selftext", ""))

    lines = [
        f"# {title}",
        f"**By u/{author}** | {score} points",
        "",
    ]

    if text:
        lines.extend([text, ""])

    return "\n".join(lines)


def format_comment(comment: dict, depth: int = 0) -> str:
    """Format a single Reddit comment as markdown.

    Args:
        comment: The comment data dict.
        depth: Nesting depth (used for indentation).

    Returns:
        Formatted markdown string.
    """
    if not comment:
        return ""

    indent = "  " * depth
    author = comment.get("author", "[deleted]")
    text = strip_html_tags(comment.get("body", ""))

    lines = [f"{indent}**u/{author}**:"]
    for line in text.split("\n"):
        lines.append(f"{indent}> {line}")
    lines.append("")

    return "\n".join(lines)


def format_thread(post: dict, comments_listing: dict) -> str:
    """Format an entire Reddit thread (post + comments) as markdown.

    Args:
        post: The post data dict.
        comments_listing: The comments listing data dict.

    Returns:
        Formatted markdown string.
    """
    lines = [format_post(post)]

    # Flatten comment tree and format
    flattened = flatten_comments(comments_listing, max_comments=50)
    for comment, depth in flattened:
        lines.append(format_comment(comment, depth))

    return "\n".join(lines)


# ============================================================================
# High-level converter
# ============================================================================

def convert_reddit(source: str, output_format: str = "markdown") -> str:
    """Convert a Reddit thread to markdown or JSON.

    Args:
        source: Reddit URL, shorthand, or post_id + subreddit.
        output_format: 'markdown' or 'json'.

    Returns:
        Formatted string (markdown or JSON).

    Raises:
        ValueError: If the source cannot be parsed.
        URLError: If the API request fails.
    """
    try:
        post_id, subreddit = extract_reddit_info(source)
    except ValueError as e:
        raise ValueError(f"Invalid Reddit source: {e}") from e

    post, comments_listing = fetch_thread(post_id, subreddit)

    if output_format == "json":
        return json.dumps({"post": post, "comments": comments_listing}, indent=2)
    else:
        return format_thread(post, comments_listing)


# ============================================================================
# CLI
# ============================================================================

def build_parser() -> argparse.ArgumentParser:
    """Build the argparse argument parser."""
    parser = argparse.ArgumentParser(
        prog="fetch-reddit",
        description="Fetch Reddit threads and format as markdown or JSON.",
        epilog=(
            "Examples:\n"
            "  fetch-reddit.py abc123 python\n"
            "  fetch-reddit.py r/python/comments/abc123\n"
            "  fetch-reddit.py https://reddit.com/r/python/comments/abc123/title\n"
            "  fetch-reddit.py abc123 python --format json | jq .\n"
            "  fetch-reddit.py abc123 python > thread.md"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "source",
        metavar="SOURCE",
        help="Reddit post ID + subreddit, URL, or r/sub/comments/id format",
    )
    parser.add_argument(
        "subreddit",
        nargs="?",
        metavar="SUBREDDIT",
        help="Subreddit name (optional, if not in SOURCE)",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format: markdown (default) or json",
    )
    return parser


def main() -> None:
    """Parse arguments and fetch/format the Reddit thread."""
    parser = build_parser()
    args = parser.parse_args()

    # Combine source and optional subreddit argument
    if args.subreddit:
        source = f"{args.source} {args.subreddit}"
    else:
        source = args.source

    try:
        result = convert_reddit(source, args.format)
        print(result)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
