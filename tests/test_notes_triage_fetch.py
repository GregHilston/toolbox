"""notes-triage-fetch.py drops share tokens, which would break clip dedupe."""

from __future__ import annotations

import unittest

from _loader import load

fetch = load("notes-triage-fetch.py")


class TestCleanUrl(unittest.TestCase):
    def test_drops_tracking_keeps_meaning(self):
        cases = {
            "https://www.instagram.com/reel/Dec-hkEAaXz/?xtok=MXR6==": "https://www.instagram.com/reel/Dec-hkEAaXz/",
            "https://www.instagram.com/reel/X/?igsh=abc&utm_source=ig": "https://www.instagram.com/reel/X/",
            "https://youtu.be/abc?si=xyz&t=42": "https://youtu.be/abc?t=42",
            "https://www.youtube.com/watch?v=abc&si=xyz": "https://www.youtube.com/watch?v=abc",
            "https://news.ycombinator.com/item?id=43753049": "https://news.ycombinator.com/item?id=43753049",
            "https://www.reddit.com/r/x/comments/1/y/?share_id=q&utm_medium=android_app": "https://www.reddit.com/r/x/comments/1/y/",
            "https://example.com/a#section": "https://example.com/a#section",
        }
        for given, want in cases.items():
            self.assertEqual(fetch.clean_url(given), want)


if __name__ == "__main__":
    unittest.main()
