#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Look something up on Wikipedia: the lead summary, or a list of matching articles.

Keyless REST and Action APIs. A title that is not exact falls back to search, so
"steam deck" finds "Steam Deck". Wikipedia asks API clients for a descriptive
User-Agent and throttles generic ones. Read a whole article with read-page.py.

Usage:
    wikipedia.py "Steam Deck"
    wikipedia.py --search "handheld gaming pc"
    wikipedia.py --lang fr "Tour Eiffel"
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.request
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode

UA = "toolbox-wikipedia/1.0 (https://github.com/GregHilston/toolbox)"


class WikiError(Exception):
    pass


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


def search(query: str, lang: str = "en", limit: int = 5) -> list[dict]:
    url = f"https://{lang}.wikipedia.org/w/api.php?" + urlencode(
        {"action": "query", "list": "search", "srsearch": query, "srlimit": limit, "format": "json"}
    )
    return [
        {
            "title": h["title"],
            "snippet": html.unescape(re.sub(r"<[^>]+>", "", h.get("snippet", ""))),
            "url": f"https://{lang}.wikipedia.org/wiki/{quote(h['title'].replace(' ', '_'), safe='()')}",
        }
        for h in _get(url)["query"]["search"]
    ]


def summary(title: str, lang: str = "en") -> dict | None:
    """The article's lead, or None when no article has exactly this title."""
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(title.replace(' ', '_'), safe='')}"
    try:
        d = _get(url)
    except HTTPError as e:
        if e.code == 404:
            return None
        raise
    return {
        "title": d["title"],
        "description": d.get("description") or "",
        "extract": d.get("extract") or "",
        "url": d["content_urls"]["desktop"]["page"],
        "disambiguation": d.get("type") == "disambiguation",
    }


def lookup(query: str, lang: str = "en") -> tuple[dict | None, list[dict]]:
    """(summary, alternatives). Alternatives are listed when the title was not exact or was ambiguous."""
    page = summary(query, lang)
    if page and not page["disambiguation"]:
        return page, []
    hits = search(query, lang)
    if page is None and hits:
        page = summary(hits[0]["title"], lang)
    return page, [h for h in hits if not page or h["title"] != page["title"]]


def format_summary(page: dict | None, others: list[dict]) -> str:
    lines = []
    if page:
        lines += [f"# {page['title']}", ""]
        if page["description"]:
            lines += [f"_{page['description']}_", ""]
        lines += [page["extract"], "", page["url"]]
    if others:
        lines += ["", "Other articles:" if page else "No exact article. Matches:"]
        lines += [f"- {h['title']}: {h['url']}" for h in others]
    return "\n".join(lines) if lines else "No Wikipedia article matches."


def format_search(hits: list[dict], query: str) -> str:
    if not hits:
        return f'No Wikipedia articles match "{query}".'
    return "\n".join(f"{i}. **{h['title']}**: {h['snippet']}\n   {h['url']}" for i, h in enumerate(hits, 1))


def main() -> None:
    parser = argparse.ArgumentParser(description="Wikipedia summary or search.")
    parser.add_argument("query")
    parser.add_argument("--search", action="store_true", help="list matching articles instead")
    parser.add_argument("--lang", default="en", help="Wikipedia language code (default: en)")
    parser.add_argument("-n", "--limit", type=int, default=5, help="search results (default: 5)")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z-]{2,12}", args.lang):
        sys.exit(f"wikipedia: {args.lang!r} is not a language code, e.g. en, fr, de")
    try:
        if args.search:
            print(format_search(search(args.query, args.lang, args.limit), args.query))
        else:
            print(format_summary(*lookup(args.query, args.lang)))
    except (URLError, TimeoutError, KeyError, ValueError) as e:
        sys.exit(f"wikipedia: {args.lang}.wikipedia.org failed: {e!r}")


if __name__ == "__main__":
    main()
