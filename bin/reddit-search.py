#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Search Reddit and print the matching threads as markdown or JSON.

Why this exists: Reddit's `search.json` endpoint is dead for cookie-authenticated
clients. It does not fail — it answers HTTP 200 with an empty `children` array, so
every caller just sees "no results". That silently breaks pi's `reddit_search`,
`reddit_pack` and `reddit_trends` tools, and `reddit-cookie-sync.sh` will still
report OK because it probes a *listing* endpoint, not a search.

The old.reddit.com HTML search still works with the same session cookie, and its
markup carries everything the JSON API used to: title, subreddit, score, comment
count, author, timestamp and a body snippet. So this scrapes that instead.

Pair it with fetch-thread.py: this finds the threads, that reads them.

Usage:
    reddit-search.py "plotter mini 5"
    reddit-search.py "pocket notebook" -r EDC -r fountainpens
    reddit-search.py "dot grid" -r notebooks -s top -t year -n 50
    reddit-search.py "waxed canvas" --format json | jq .

Examples:
    reddit-search.py "refillable notebook cover" -r EDC -n 25
    reddit-search.py "tomoe river" -s top -t all --format json
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError

try:
    from fetch_reddit import load_reddit_cookie
except ImportError as e:  # pragma: no cover - only trips if bin/ layout changes
    print(f"Error: could not import fetch_reddit: {e}", file=sys.stderr)
    print("reddit-search.py expects fetch_reddit.py in the same directory.", file=sys.stderr)
    sys.exit(1)

BASE_URL = "https://old.reddit.com"

# old.reddit serves the modern layout to a JSON-ish user agent and the classic
# markup this parser expects to a browser one, so claim to be a browser.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

RESULTS_PER_PAGE = 25

AUTH_HINT = (
    "\nReddit requires a session cookie on search.\n"
    "Log in to reddit.com in Firefox, then run:\n"
    "  ~/Git/toolbox/bin/reddit-cookie-sync.sh\n"
    "(or write the cookie by hand to ~/.config/pi-reddit-research/cookie.txt)."
)

# One search result block, split on the post fullname that opens each one.
RESULT_SPLIT = re.compile(r'data-fullname="(t3_[a-z0-9]+)"')

FIELD_PATTERNS = {
    "title": re.compile(r'class="search-title[^"]*"[^>]*>(.*?)</a>', re.S),
    "url": re.compile(r'<a href="(https://old\.reddit\.com/r/[^"]+/comments/[^"]+)"'),
    "score": re.compile(r'class="search-score">([-\d]+)\s*points?</span>'),
    "comments": re.compile(r'class="search-comments[^"]*"[^>]*>(\d+)\s*comments?</a>'),
    "created": re.compile(r'<time[^>]*datetime="([^"]+)"'),
    "author": re.compile(r'class="search-author">by\s*(?:&#32;)?<a href="[^"]*/user/([^/"]+)"'),
    "subreddit": re.compile(r'class="search-subreddit-link[^"]*"[^>]*>r/([A-Za-z0-9_]+)</a>'),
    "body": re.compile(r'class="search-result-body">(.*?)</div>\s*</div>', re.S),
}

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def clean(fragment: str | None) -> str:
    """Strip tags and entities out of a snippet of Reddit's markup."""
    if not fragment:
        return ""
    return WS_RE.sub(" ", html.unescape(TAG_RE.sub(" ", fragment))).strip()


def build_search_url(
    query: str,
    subreddits: list[str],
    sort: str,
    period: str,
    after: str | None,
    count: int,
) -> str:
    params = {"q": query, "sort": sort, "t": period}
    if subreddits:
        # A multireddit path plus restrict_sr scopes the search to just these subs.
        path = f"/r/{'+'.join(subreddits)}/search"
        params["restrict_sr"] = "on"
    else:
        path = "/search"
    if after:
        params["after"] = after
        params["count"] = str(count)
    return f"{BASE_URL}{path}?{urllib.parse.urlencode(params)}"


def fetch(url: str, cookie: str | None) -> str:
    request = urllib.request.Request(url)
    request.add_header("User-Agent", USER_AGENT)
    if cookie:
        request.add_header("Cookie", cookie)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8", errors="replace")
    except HTTPError as e:
        if e.code in (401, 403):
            reason = (
                "no Reddit cookie found"
                if not cookie
                else "the configured Reddit cookie was rejected (it has probably expired)"
            )
            print(f"Error: HTTP {e.code} from Reddit search — {reason}.{AUTH_HINT}", file=sys.stderr)
            sys.exit(1)
        if e.code == 429:
            print("Error: HTTP 429 — Reddit is rate limiting. Wait a minute and retry.", file=sys.stderr)
            sys.exit(1)
        print(f"Error: HTTP {e.code} fetching {url}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Error: could not reach Reddit: {e.reason}", file=sys.stderr)
        sys.exit(1)


def parse_results(page: str) -> list[dict]:
    """Pull the search-result blocks out of one page of old.reddit HTML."""
    chunks = RESULT_SPLIT.split(page)
    # split() gives [preamble, id, block, id, block, ...]
    results = []
    for post_id, block in zip(chunks[1::2], chunks[2::2]):
        fields = {}
        for name, pattern in FIELD_PATTERNS.items():
            match = pattern.search(block)
            fields[name] = match.group(1) if match else None
        if not fields["url"]:
            continue  # promoted slot or a malformed block
        results.append(
            {
                "id": post_id.removeprefix("t3_"),
                "title": clean(fields["title"]),
                "url": fields["url"].replace("old.reddit.com", "www.reddit.com"),
                "subreddit": fields["subreddit"] or "",
                "score": int(fields["score"]) if fields["score"] else 0,
                "comments": int(fields["comments"]) if fields["comments"] else 0,
                "created": (fields["created"] or "")[:10],
                "author": fields["author"] or "",
                "snippet": clean(fields["body"])[:400],
            }
        )
    return results


def search(
    query: str,
    subreddits: list[str],
    sort: str,
    period: str,
    limit: int,
) -> list[dict]:
    cookie = load_reddit_cookie()
    results: list[dict] = []
    after: str | None = None
    count = 0

    while len(results) < limit:
        url = build_search_url(query, subreddits, sort, period, after, count)
        page = fetch(url, cookie)
        batch = parse_results(page)

        if not batch:
            # An empty first page with a login form means the cookie is the problem;
            # an empty page later just means we reached the end of the results.
            if not results and ("login" in page.lower() and "search-result" not in page):
                print(f"Error: Reddit returned no results and a login page.{AUTH_HINT}", file=sys.stderr)
                sys.exit(1)
            break

        results.extend(batch)
        if len(batch) < RESULTS_PER_PAGE:
            break

        after = f"t3_{batch[-1]['id']}"
        count += len(batch)
        time.sleep(1)  # be a polite scraper

    return results[:limit]


def format_markdown(results: list[dict], query: str, subreddits: list[str], sort: str, period: str) -> str:
    scope = ", ".join(f"r/{s}" for s in subreddits) if subreddits else "all of Reddit"
    lines = [
        f'# Reddit search: "{query}"',
        "",
        f"scope: {scope} | sort: {sort} | time: {period} | {len(results)} result"
        f"{'' if len(results) == 1 else 's'}",
        "",
    ]
    if not results:
        lines.append("_No results._")
        return "\n".join(lines)

    for i, r in enumerate(results, 1):
        lines.append(f"{i}. **{r['title']}**")
        meta = f"   r/{r['subreddit']} · {r['score']} points · {r['comments']} comments · {r['created']}"
        if r["author"]:
            meta += f" · u/{r['author']}"
        lines.append(meta)
        lines.append(f"   {r['url']}")
        if r["snippet"]:
            lines.append(f"   > {r['snippet']}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search Reddit via old.reddit HTML (the JSON search endpoint returns nothing).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  reddit-search.py "plotter mini 5"
  reddit-search.py "pocket notebook" -r EDC -r fountainpens
  reddit-search.py "dot grid" -r notebooks -s top -t year -n 50
  reddit-search.py "tomoe river" --format json | jq .

Then read a thread with:
  fetch-thread.py <url>
""",
    )
    parser.add_argument("query", help="search query")
    parser.add_argument(
        "-r",
        "--subreddit",
        action="append",
        default=[],
        metavar="NAME",
        help="restrict to a subreddit (repeatable)",
    )
    parser.add_argument(
        "-s",
        "--sort",
        default="relevance",
        choices=["relevance", "hot", "top", "new", "comments"],
        help="sort order (default: relevance)",
    )
    parser.add_argument(
        "-t",
        "--time",
        dest="period",
        default="all",
        choices=["hour", "day", "week", "month", "year", "all"],
        help="time window (default: all)",
    )
    parser.add_argument("-n", "--limit", type=int, default=25, help="max results (default: 25)")
    parser.add_argument(
        "--format", default="markdown", choices=["markdown", "json"], help="output format"
    )
    args = parser.parse_args()

    subreddits = [s.removeprefix("r/").strip("/") for s in args.subreddit]
    results = search(args.query, subreddits, args.sort, args.period, args.limit)

    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        print(format_markdown(results, args.query, subreddits, args.sort, args.period))


if __name__ == "__main__":
    main()
