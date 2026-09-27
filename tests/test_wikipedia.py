"""wikipedia.py summarises, falls back to search, and lists ambiguities.

Fixtures are trimmed real responses (2026-09-27); upstream drift shows up
in test_keyless_tools_live.py instead.
"""

from __future__ import annotations

import unittest
from unittest import mock
from urllib.error import HTTPError

from _loader import load

wiki = load("wikipedia.py")


def _http_404(url: str) -> HTTPError:
    return HTTPError(url, 404, "Not Found", {}, None)


SUMMARY = {"type": "standard", "title": "Steam Deck", "description": "Handheld gaming computer by Valve",
           "extract": "The Steam Deck is a handheld gaming computer.",
           "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Steam_Deck"}}}
SEARCH = {"query": {"search": [
    {"title": "Steam Deck", "snippet": 'the <span class="searchmatch">Steam</span> &quot;Deck&quot;'},
    {"title": "SteamOS", "snippet": "an OS"},
]}}


class TestWikipedia(unittest.TestCase):
    def test_an_exact_title_needs_no_search(self):
        with mock.patch.object(wiki, "_get", return_value=SUMMARY) as get:
            found, others = wiki.lookup("Steam Deck")
        self.assertEqual((found["title"], others), ("Steam Deck", []))
        self.assertEqual(get.call_count, 1)

    def test_an_inexact_title_falls_back_to_search(self):
        def get(url):
            if "/page/summary/steam_deck" in url:
                raise _http_404(url)
            return SEARCH if "list=search" in url else SUMMARY
        with mock.patch.object(wiki, "_get", side_effect=get):
            found, others = wiki.lookup("steam deck")
        self.assertEqual(found["title"], "Steam Deck")
        self.assertEqual([h["title"] for h in others], ["SteamOS"], "the chosen article is not listed again")

    def test_a_disambiguation_page_lists_the_candidates(self):
        disamb = {**SUMMARY, "type": "disambiguation", "title": "Mercury"}
        with mock.patch.object(wiki, "_get", side_effect=lambda url: SEARCH if "list=search" in url else disamb):
            found, others = wiki.lookup("Mercury")
        self.assertTrue(found["disambiguation"])
        self.assertEqual(len(others), 2)

    def test_snippets_lose_markup(self):
        with mock.patch.object(wiki, "_get", return_value=SEARCH):
            hits = wiki.search("steam")
        self.assertEqual(hits[0]["snippet"], 'the Steam "Deck"')
        self.assertEqual(hits[0]["url"], "https://en.wikipedia.org/wiki/Steam_Deck")

    def test_nothing_found(self):
        self.assertEqual(wiki.format_summary(None, []), "No Wikipedia article matches.")


if __name__ == "__main__":
    unittest.main()
