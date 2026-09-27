"""Is Reddit still reachable without a login? Hits reddit.com, so opt-in.

    REDDIT_LIVE=1 python3 -m unittest test_fetch_reddit_live -v

A failure here, with test_fetch_reddit.py passing, means Reddit changed and
fetch_reddit.py needs updating. Each message says what changed.
"""

from __future__ import annotations

import os
import time
import unittest

from _loader import load

fr = load("fetch_reddit.py")

# A busy, long-lived thread, so "no comments" can only mean breakage.
SUB, POST = "hermesagent", "1wmbj0u"


@unittest.skipUnless(os.environ.get("REDDIT_LIVE"), "set REDDIT_LIVE=1 to call reddit.com")
class TestRedditLive(unittest.TestCase):
    def tearDown(self):
        time.sleep(1.5)

    def test_search(self):
        posts, next_page = fr.parse_search(fr.get("/svc/shreddit/search/?q=hermes+agent&type=posts"))
        self.assertTrue(posts, "search returned a page with no results: the sdui-post-unit markup changed")
        self.assertTrue(all(p.title and p.subreddit for p in posts), "search results lost their title links")
        self.assertIsNotNone(posts[0].score, "the search-counter-row vote count moved")
        self.assertTrue(next_page, "no cursor partial: search pagination changed")

    def test_thread_comments(self):
        comments, more = fr.parse_comments(fr.get(f"/svc/shreddit/comments/r/{SUB}/t3_{POST}?sort=top"))
        self.assertTrue(comments, "no <shreddit-comment> elements: the comments partial changed")
        self.assertTrue(all(c.body for c in comments), "comment bodies came back empty: *-comment-rtjson-content moved")
        self.assertTrue(any(c.parent_id for c in comments), "no reply has a parentId: nesting changed")
        self.assertTrue(more, "no top-level more-comments partial: pagination changed")
        time.sleep(1.5)
        batch, _ = fr.parse_comments(fr.get(more[0], {"cursor": more[1]}))
        self.assertTrue(batch, "the more-comments POST returned nothing: its form changed")

    def test_post_feed(self):
        try:
            post = fr.parse_post_rss(fr.get(f"/r/{SUB}/comments/{POST}/.rss?limit=1"), SUB, POST)
        except fr.RedditError as e:
            if "429" in str(e):
                self.skipTest("RSS is rate-limited to ~1 request a minute; retry shortly")
            raise
        self.assertTrue(post.title and post.body, "the thread feed lost its title or content")


if __name__ == "__main__":
    unittest.main()
