"""steam-game.py finds a game and reads Steam, the Deck report and ProtonDB.

Fixtures are trimmed real responses (2026-09-27); upstream drift shows up
in test_keyless_tools_live.py instead.
"""

from __future__ import annotations

import unittest
from unittest import mock

from _loader import load

steam = load("steam-game.py")


HADES = {"name": "Hades", "is_free": False, "developers": ["Supergiant Games"],
         "release_date": {"coming_soon": False, "date": "Sep 17, 2020"},
         "genres": [{"description": "Action"}, {"description": "RPG"}], "short_description": "Defy the god of the dead.",
         "price_overview": {"discount_percent": 75, "final_formatted": "$6.24", "initial_formatted": "$24.99"},
         "platforms": {"windows": True, "linux": False}, "metacritic": {"score": 93}}
REVIEWS = {"review_score_desc": "Overwhelmingly Positive", "total_positive": 98, "total_reviews": 100}
DECK = {"resolved_category": 3, "steamos_resolved_category": 2, "resolved_items": [
    {"display_type": 4, "loc_token": "#SteamDeckVerified_TestResult_InterfaceTextIsLegible"},
    {"display_type": 1, "loc_token": "#SteamDeckVerified_TestResult_ExternalControllersNotSupportedPrimaryPlayer"},
]}
PROTON = {"tier": "platinum", "total": 751, "confidence": "strong", "trendingTier": "gold"}


class TestSteamGame(unittest.TestCase):
    def test_an_id_or_store_url_skips_search(self):
        self.assertEqual(steam.find("1145360", "us"), (1145360, []))
        self.assertEqual(steam.find("https://store.steampowered.com/app/1145360/Hades/", "us")[0], 1145360)

    def test_an_exact_name_beats_relevance(self):
        items = {"items": [{"type": "app", "id": 2, "name": "Hades II"}, {"type": "app", "id": 1, "name": "Hades"}]}
        with mock.patch.object(steam, "_get", return_value=items):
            self.assertEqual(steam.find("hades", "us"), (1, [{"id": 2, "name": "Hades II"}]))

    def test_no_match_says_so(self):
        with mock.patch.object(steam, "_get", return_value={"items": []}):
            with self.assertRaisesRegex(steam.SteamError, "no Steam game"):
                steam.find("zzz", "us")

    def test_details_are_keyed_by_whatever_id_steam_chooses(self):
        with mock.patch.object(steam, "_get", return_value={"1206340": {"success": True, "data": HADES}}):
            self.assertEqual(steam.details(1145360, "us")["name"], "Hades")

    def test_the_card(self):
        out = steam.format_game(1145360, HADES, REVIEWS, DECK, PROTON, [])
        for line in ("Price: $6.24 (75% off $24.99)",
                     "Steam reviews: Overwhelmingly Positive, 98% positive of 100",
                     "Steam Deck: Verified (notes: External controllers not supported primary player)",
                     "SteamOS: Compatible", "Native Linux build: no",
                     "ProtonDB: Platinum (751 reports, strong confidence, trending Gold)"):
            self.assertIn(line, out)

    def test_missing_ratings_read_as_missing(self):
        out = steam.format_game(1, {**HADES, "price_overview": None, "metacritic": None}, {}, {}, None, [])
        for line in ("Price: not for sale", "Steam reviews: none yet", "Steam Deck: Unknown", "ProtonDB: no reports"):
            self.assertIn(line, out)


if __name__ == "__main__":
    unittest.main()
