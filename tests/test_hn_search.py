"""hn-search.py turns Algolia's response into stories and markdown."""

from __future__ import annotations

import json
import unittest
from unittest import mock

from _loader import load

hn = load("hn-search.py")

HIT = {"objectID": "43186523", "title": "Plotter Notebook System", "url": "https://arslan.io/x",
       "points": 6, "num_comments": 1, "created_at": "2025-02-26T18:28:48Z", "author": "Brajeshwar"}


def _response(body: dict) -> mock.MagicMock:
    resp = mock.MagicMock()
    resp.__enter__.return_value = resp
    resp.read.return_value = json.dumps(body).encode()
    return resp


class TestHnSearch(unittest.TestCase):
    def test_a_hit_becomes_a_story_with_its_thread_link(self):
        with mock.patch.object(hn.urllib.request, "urlopen", return_value=_response({"hits": [HIT]})) as urlopen:
            stories = hn.search("plotter", limit=1)
        self.assertIn("/search?", urlopen.call_args.args[0])
        self.assertEqual(stories[0]["thread"], "https://news.ycombinator.com/item?id=43186523")
        self.assertEqual((stories[0]["points"], stories[0]["comments"], stories[0]["created"]), (6, 1, "2025-02-26"))

    def test_sorting_by_date_uses_the_date_endpoint(self):
        with mock.patch.object(hn.urllib.request, "urlopen", return_value=_response({"hits": []})) as urlopen:
            hn.search("x", by_date=True)
        self.assertIn("/search_by_date?", urlopen.call_args.args[0])

    def test_markdown(self):
        out = hn.format_markdown([{
            "title": "T", "thread": "https://news.ycombinator.com/item?id=1", "url": "", "points": 2,
            "comments": 3, "created": "2025-01-01", "author": "a"}], "q")
        self.assertIn("2 points · 3 comments", out)
        self.assertNotIn("links to", out, "a text post has no outbound link")


if __name__ == "__main__":
    unittest.main()
