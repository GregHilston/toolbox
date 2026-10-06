#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Search Hacker News stories. Read one with fetch-thread.py.

Uses HN's Algolia search API, which needs no key. Hermes bots have no
web search tool, so this is how they find a thread to read.

Usage:
    hn-search.py "plotter notebook"
    hn-search.py "rust async" -s date -n 20
    hn-search.py "sqlite" --format json | jq .
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from urllib.error import URLError
from urllib.parse import urlencode

API = "https://hn.algolia.com/api/v1"


def search(query: str, by_date: bool = False, limit: int = 10) -> list[dict]:
    """Stories matching `query`, most relevant (or newest) first."""
    endpoint = "search_by_date" if by_date else "search"
    url = f"{API}/{endpoint}?" + urlencode({"query": query, "tags": "story", "hitsPerPage": limit})
    with urllib.request.urlopen(url, timeout=20) as resp:
        hits = json.loads(resp.read())["hits"]
    return [
        {
            "title": h.get("title") or "",
            "thread": f"https://news.ycombinator.com/item?id={h['objectID']}",
            "url": h.get("url") or "",
            "points": h.get("points"),
            "comments": h.get("num_comments"),
            "created": (h.get("created_at") or "")[:10],
            "author": h.get("author") or "",
        }
        for h in hits
    ]


def format_markdown(stories: list[dict], query: str) -> str:
    lines = [f'# Hacker News search: "{query}"', ""]
    if not stories:
        return "\n".join(lines + ["_No results._"])
    for i, s in enumerate(stories, 1):
        lines.append(f"{i}. **{s['title']}**")
        lines.append(f"   {s['points']} points · {s['comments']} comments · {s['created']} · {s['author']}")
        lines.append(f"   {s['thread']}")
        if s["url"]:
            lines.append(f"   links to {s['url']}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Search Hacker News. Read a thread with: fetch-thread.py <url>")
    parser.add_argument("query")
    parser.add_argument("-s", "--sort", default="relevance", choices=["relevance", "date"])
    parser.add_argument("-n", "--limit", type=int, default=10, help="max results (default: 10)")
    parser.add_argument("--format", default="markdown", choices=["markdown", "json"])
    args = parser.parse_args()
    try:
        stories = search(args.query, args.sort == "date", args.limit)
    except (URLError, TimeoutError, KeyError, ValueError) as e:
        sys.exit(f"hn-search: Algolia's HN search failed: {e!r}")
    print(json.dumps(stories, indent=2) if args.format == "json" else format_markdown(stories, args.query))


if __name__ == "__main__":
    main()
