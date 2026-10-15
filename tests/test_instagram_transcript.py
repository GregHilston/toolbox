"""instagram-transcript.py sends moria only the URL shape its forced command accepts."""

from __future__ import annotations

import re
import unittest

from _loader import BIN, load

ig = load("instagram-transcript.py")


class TestCanonical(unittest.TestCase):
    def test_strips_query_and_normalises(self):
        cases = {
            "https://www.instagram.com/reel/Dec-hkEAaXz/?xtok=MXR6==": "https://www.instagram.com/reel/Dec-hkEAaXz/",
            "instagram.com/reels/Abc_1": "https://www.instagram.com/reel/Abc_1/",
            "https://instagram.com/p/XYZ/?igsh=1": "https://www.instagram.com/p/XYZ/",
        }
        for given, want in cases.items():
            self.assertEqual(ig.canonical(given), want)

    def test_rejects_other_urls(self):
        with self.assertRaises(SystemExit):
            ig.canonical("https://www.instagram.com/someuser/")

    def test_moria_side_accepts_every_canonical_url(self):
        # The two regexes must agree, or every call fails.
        sh = (BIN / "instagram-transcribe-moria.sh").read_text()
        pattern = re.search(r"\[\[ ! \$url =~ (\S+) \]\]", sh)[1]
        for url in ("https://www.instagram.com/reel/Dec-hkEAaXz/", "https://www.instagram.com/p/XYZ/"):
            self.assertRegex(ig.canonical(url), pattern)


if __name__ == "__main__":
    unittest.main()
