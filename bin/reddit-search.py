#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Search Reddit for threads, without a login. Read one with fetch-thread.py.

Goes through fetch_reddit.py, which explains why the endpoint is what it is.
Reddit's search is fuzzy: a query with no real match still returns posts.

Usage:
    reddit-search.py "plotter mini 5"
    reddit-search.py "pocket notebook" -r EDC -r fountainpens
    reddit-search.py "dot grid" -r notebooks -s top -t year -n 50
    reddit-search.py "tomoe river" --format json | jq .
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from fetch_reddit import Post, RedditError, search


def format_markdown(posts: list[Post], query: str, subreddits: list[str], sort: str, period: str) -> str:
    scope = ", ".join(f"r/{s}" for s in subreddits) if subreddits else "all of Reddit"
    lines = [f'# Reddit search: "{query}"', "", f"scope: {scope} | sort: {sort} | time: {period}", ""]
    if not posts:
        return "\n".join(lines + ["_No results._"])
    for i, p in enumerate(posts, 1):
        lines.append(f"{i}. **{p.title}**")
        lines.append(f"   r/{p.subreddit} · {p.score} votes · {p.comments} comments · {p.created[:10]} · u/{p.author}")
        lines.append(f"   {p.url}")
        if p.snippet:
            lines.append(f"   > {p.snippet}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search Reddit without a login. Read a thread with: fetch-thread.py <url>",
    )
    parser.add_argument("query", help="search query")
    parser.add_argument(
        "-r", "--subreddit", action="append", default=[], metavar="NAME", help="search only this subreddit (repeatable)"
    )
    parser.add_argument(
        "-s", "--sort", default="relevance", choices=["relevance", "hot", "top", "new", "comments"]
    )
    parser.add_argument(
        "-t", "--time", dest="period", default="all", choices=["hour", "day", "week", "month", "year", "all"]
    )
    parser.add_argument("-n", "--limit", type=int, default=25, help="max results per subreddit (default: 25)")
    parser.add_argument("--format", default="markdown", choices=["markdown", "json"])
    args = parser.parse_args()

    subreddits = [s.removeprefix("r/").strip("/") for s in args.subreddit]
    try:
        # Reddit's partial rejects a multireddit, so search each sub on its own.
        posts = [p for sub in subreddits or [""] for p in search(args.query, sub, args.sort, args.period, args.limit)]
    except RedditError as e:
        sys.exit(f"reddit-search: {e}")

    if args.format == "json":
        print(json.dumps([asdict(p) for p in posts], indent=2))
    else:
        print(format_markdown(posts, args.query, subreddits, args.sort, args.period))


if __name__ == "__main__":
    main()
