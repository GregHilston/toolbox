"""fetch_reddit's parsers against real Reddit pages, and its error messages.

The fixtures under fixtures/reddit/ are captured responses (2026-09-26), with
<style>, <svg>, <script>, class and style stripped for size. A failure here is
our bug. A failure only in test_fetch_reddit_live.py means Reddit changed.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError

from _loader import load

fr = load("fetch_reddit.py")
triage = load("notes-triage-fetch.py")

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "reddit"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


class TestParseSearch(unittest.TestCase):
    def setUp(self):
        self.posts, self.next_page = fr.parse_search(fixture("search.html"))

    def test_every_result_is_parsed(self):
        self.assertEqual(len(self.posts), 7)

    def test_fields(self):
        p = self.posts[0]
        self.assertEqual(p.id, "1ujelu0")
        self.assertEqual(p.subreddit, "PlotterNotebook")
        self.assertEqual(p.title, "My perfect (for me) plotter mini5 wallet")
        self.assertEqual(p.author, "Optimal_Mix6097")
        self.assertEqual((p.score, p.comments), (118, 17))
        self.assertTrue(p.created.startswith("2026-06-30"))
        self.assertTrue(p.url.startswith("https://www.reddit.com/r/PlotterNotebook/comments/1ujelu0/"))
        self.assertIn("plotter rings", p.snippet)

    def test_next_page_is_an_unescaped_path(self):
        self.assertTrue(self.next_page.startswith("/svc/shreddit/search/?q=plotter+mini+5&type=posts"))
        self.assertIn("&cursor=", self.next_page)
        self.assertNotIn("&amp;", self.next_page)

    def test_a_page_with_no_results(self):
        self.assertEqual(fr.parse_search("<html></html>"), ([], None))


class TestParseComments(unittest.TestCase):
    def setUp(self):
        self.comments, self.more = fr.parse_comments(fixture("thread.html"))

    def test_every_comment_has_a_body(self):
        self.assertEqual(len(self.comments), 25)
        self.assertEqual([c.id for c in self.comments if not c.body], [])

    def test_fields(self):
        c = self.comments[0]
        self.assertEqual((c.id, c.parent_id, c.author, c.score, c.depth), ("pb5i2zb", "", "Broer1", 26, 0))
        self.assertEqual(c.body, "i drove my BMW against a wall. Please don't buy a BMW.")

    def test_nesting(self):
        by_id = {c.id: c for c in self.comments}
        self.assertEqual(by_id["pb679ie"].parent_id, "pb5i2zb")
        self.assertEqual(by_id["pban6xd"].depth, 2)
        self.assertEqual(by_id["pban6xd"].parent_id, "pb67g4t")

    def test_top_level_pagination(self):
        path, cursor = self.more
        self.assertTrue(path.startswith("/svc/shreddit/more-comments/hermesagent/t3_1wmbj0u?"))
        self.assertIn("top-level=1", path)
        self.assertTrue(cursor)

    def test_the_last_batch_has_no_more(self):
        comments, more = fr.parse_comments(fixture("more-comments.html"))
        self.assertEqual(len(comments), 7)
        self.assertIsNone(more)


class TestParsePostRss(unittest.TestCase):
    def test_the_post(self):
        p = fr.parse_post_rss(fixture("thread.rss"), "hermesagent", "1wmbj0u")
        self.assertEqual(p.title, "If you're thinking of trying out Hermes agent - don't")
        self.assertEqual(p.author, "Upstairs_Score4983")
        self.assertTrue(p.body.startswith("Seriously, I don't know"))
        self.assertIn("\n- Creates random directories", p.body, "list items stay on their own lines")


class TestExtractRedditInfo(unittest.TestCase):
    def test_forms(self):
        for source in (
            "https://www.reddit.com/r/python/comments/abc123/title/",
            "https://old.reddit.com/r/python/comments/abc123",
            "r/python/comments/abc123",
            "abc123 python",
        ):
            self.assertEqual(fr.extract_reddit_info(source), ("abc123", "python"), source)

    def test_garbage(self):
        with self.assertRaises(ValueError):
            fr.extract_reddit_info("https://example.com/")


def _response(url: str, body: str = "") -> mock.MagicMock:
    resp = mock.MagicMock()
    resp.__enter__.return_value = resp
    resp.geturl.return_value = url
    resp.read.return_value = body.encode()
    return resp


class TestGetErrors(unittest.TestCase):
    """Each way Reddit can shut the door gets a message that names it."""

    def _raises(self, effect) -> str:
        with mock.patch.object(fr.urllib.request, "urlopen", side_effect=effect):
            with self.assertRaises(fr.RedditError) as ctx:
                fr.get("/svc/shreddit/search/?q=x")
        return str(ctx.exception)

    def _http(self, code: int) -> HTTPError:
        return HTTPError("https://www.reddit.com/x", code, "no", {}, None)

    def test_403_blames_the_user_agent(self):
        self.assertIn("User-Agent", self._raises(self._http(403)))

    def test_429_says_slow_down(self):
        self.assertIn("rate-limited", self._raises(self._http(429)))

    def test_a_login_redirect_says_walled(self):
        msg = self._raises([_response("https://www.reddit.com/login/?reason=lor2")])
        self.assertIn("login-walled", msg)

    def test_a_dropped_connection_is_a_reddit_error(self):
        self.assertIn("failed mid-response", self._raises(ConnectionResetError("reset")))

    def test_a_subreddit_named_login_is_not_a_wall(self):
        url = "https://www.reddit.com/svc/shreddit/more-comments/loginhelp/t3_x"
        with mock.patch.object(fr.urllib.request, "urlopen", return_value=_response(url, "ok")):
            self.assertEqual(fr.get("/x"), "ok")

    def test_success_returns_the_body(self):
        with mock.patch.object(fr.urllib.request, "urlopen", return_value=_response("https://www.reddit.com/x", "ok")):
            self.assertEqual(fr.get("/x"), "ok")


class TestFetchThread(unittest.TestCase):
    def _fetch(self, feed, **kwargs):
        self.paths = []

        def fake_get(path, form=None):
            self.paths.append(path)
            if path.endswith(".rss?limit=1"):
                return feed()
            return fixture("thread.html") if form is None else fixture("more-comments.html")

        with mock.patch.object(fr, "get", side_effect=fake_get), mock.patch.object(fr.time, "sleep"):
            return fr.fetch_thread("1wmbj0u", "hermesagent", **kwargs)

    def test_a_rate_limited_feed_still_returns_the_comments(self):
        def feed():
            raise fr.RedditError("HTTP 429 on feed: rate-limited.")

        post, comments = self._fetch(feed, limit=50)
        self.assertIn("rate-limited", post.body)
        self.assertEqual(len(comments), 32, "first page plus one more-comments batch")

    def test_a_feed_that_is_not_atom_still_returns_the_comments(self):
        post, comments = self._fetch(lambda: "<html>interstitial</html>")
        self.assertIn("unavailable", post.body)
        self.assertEqual(len(comments), 25)

    def test_the_default_limit_costs_no_extra_requests(self):
        self._fetch(lambda: fixture("thread.rss"))
        self.assertEqual(len(self.paths), 2, "feed + first comments page only")

    def test_a_comment_id_focuses_the_page(self):
        self._fetch(lambda: fixture("thread.rss"), comment_id="pban6xd")
        self.assertTrue(self.paths[1].startswith("/svc/shreddit/comments/r/hermesagent/t3_1wmbj0u/t1_pban6xd?"))


class TestCommentContext(unittest.TestCase):
    def setUp(self):
        self.comments, _ = fr.parse_comments(fixture("thread.html"))

    def test_ancestors_the_comment_and_its_replies(self):
        ids = [c.id for c in triage.comment_context(self.comments, "pb67g4t")]
        self.assertEqual(ids, ["pb5hpom", "pb67g4t", "pban6xd"])

    def test_an_unloaded_comment_keeps_the_whole_thread(self):
        self.assertEqual(len(triage.comment_context(self.comments, "nothere")), 25)

    def test_an_unloaded_comment_is_called_out(self):
        post = fr.parse_post_rss(fixture("thread.rss"), "hermesagent", "1wmbj0u")
        it = triage.Item(url="https://www.reddit.com/r/hermesagent/comments/1wmbj0u/comment/nothere/")
        with mock.patch.object(triage, "fetch_reddit_thread", return_value=(post, self.comments)):
            triage.fetch_reddit_comment(it)
        self.assertTrue(it.body.startswith("(saved comment nothere was not in the loaded comments"))


if __name__ == "__main__":
    unittest.main()
