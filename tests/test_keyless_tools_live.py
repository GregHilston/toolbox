"""Do the keyless APIs behind weather, wikipedia, steam-game and read-page still answer? Opt-in.

    KEYLESS_LIVE=1 python3 -m unittest test_keyless_tools_live -v

A failure here, with the offline tests passing, means an upstream changed.
"""

from __future__ import annotations

import os
import unittest

from _loader import load

weather = load("weather.py")
wiki = load("wikipedia.py")
steam = load("steam-game.py")
page = load("read-page.py")


@unittest.skipUnless(os.environ.get("KEYLESS_LIVE"), "set KEYLESS_LIVE=1 to call the real APIs")
class TestKeylessLive(unittest.TestCase):
    def test_open_meteo(self):
        label, lat, lon = weather.geocode("Burlington, VT")
        self.assertIn("Vermont", label, "geocoding lost admin1, or its ranking moved")
        w = weather.parse(weather.fetch(lat, lon, 2), label)
        self.assertEqual(len(w["days"]), 2)
        self.assertEqual(len(w["hours"]), 24, "hourly rows no longer line up with today")

    def test_wikipedia(self):
        found, _ = wiki.lookup("steam deck")
        self.assertEqual(found["title"], "Steam Deck", "the summary 404 no longer falls back to search")
        self.assertTrue(found["extract"])

    def test_steam(self):
        appid, _ = steam.find("Hades", "us")
        self.assertEqual(appid, 1145360)
        self.assertEqual(steam.details(appid, "us")["name"], "Hades")
        self.assertTrue(steam.reviews(appid).get("total_reviews"), "appreviews lost query_summary")
        self.assertEqual(steam.deck(appid).get("resolved_category"), 3, "the Deck report changed shape")
        self.assertTrue(steam.protondb(appid), "ProtonDB's summary file moved")

    def test_read_page(self):
        title, body, via = page.read("https://simonwillison.net/2024/Dec/19/one-shot-python-tools/")
        self.assertEqual(via, "defuddle", "defuddle failed on a plain blog post")
        self.assertIn("one-shot", title)

    def test_jina(self):
        self.assertIsNotNone(page.jina("https://simonwillison.net/2024/Dec/19/one-shot-python-tools/"))


if __name__ == "__main__":
    unittest.main()
