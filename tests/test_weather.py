"""weather.py turns Open-Meteo responses into a forecast, and finds towns.

Fixtures are trimmed real responses (2026-09-27); upstream drift shows up
in test_keyless_tools_live.py instead.
"""

from __future__ import annotations

import unittest
from unittest import mock

from _loader import load

weather = load("weather.py")


FORECAST = {
    "current": {"time": "2026-01-10T09:00", "temperature_2m": 12.4, "apparent_temperature": 3.1,
                "weather_code": 73, "wind_speed_10m": 9.6},
    "daily": {
        "time": ["2026-01-09", "2026-01-10", "2026-01-11"],
        "temperature_2m_max": [30.0, 21.0, 25.0],
        "temperature_2m_min": [12.0, 4.0, 9.0],
        "precipitation_sum": [0.0, 0.31, None],
        "precipitation_probability_max": [0, 80, None],
        "weather_code": [3, 73, 999],
    },
    "hourly": {
        "time": [f"2026-01-{d}T{h:02d}:00" for d in ("09", "10", "11") for h in range(24)],
        "temperature_2m": [float(h) for _ in range(3) for h in range(24)],
        "precipitation_probability": [None] * 72,
        "precipitation": [0.0] * 72,
        "weather_code": [73] * 72,
    },
}

BURLINGTONS = {"results": [
    {"name": "Burlington", "admin1": "Ontario", "country": "Canada", "country_code": "CA", "latitude": 43.3, "longitude": -79.8},
    {"name": "Burlington", "admin1": "Vermont", "country": "United States", "country_code": "US", "latitude": 44.5, "longitude": -73.2},
]}


class TestWeather(unittest.TestCase):
    def setUp(self):
        self.w = weather.parse(FORECAST, "Sheldon, VT")

    def test_yesterday_is_split_from_the_forecast_days(self):
        self.assertEqual(self.w["yesterday"]["high_f"], 30.0)
        self.assertEqual([d["date"] for d in self.w["days"]], ["2026-01-10", "2026-01-11"])

    def test_only_todays_hours(self):
        self.assertEqual(len(self.w["hours"]), 24)
        self.assertEqual(self.w["hours"][0]["time"], "2026-01-10T00:00")
        self.assertEqual(self.w["hours"][0]["precip_chance"], 0, "a null chance reads as 0")

    def test_codes_are_named_and_unknown_ones_survive(self):
        self.assertEqual(self.w["now"]["summary"], "Snow")
        self.assertEqual(self.w["days"][1]["summary"], "Unknown")

    def test_text(self):
        out = weather.format_text(self.w)
        self.assertIn("Now: Snow, 12°F (feels 3°F), wind 10 mph", out)
        self.assertIn("Sat Jan 10: Snow, high 21°F, low 4°F, 80% chance, 0.31 in", out)
        self.assertIn("Sun Jan 11: Unknown, high 25°F, low 9°F, dry", out)

    def test_the_json_keys_the_digest_reads(self):
        # home-lab's digest/weather.py parses these; renaming one drops its weather card.
        day = {"date", "high_f", "low_f", "precip_in", "precip_chance", "summary", "icon"}
        self.assertLessEqual({"location", "yesterday", "days", "hours"}, set(self.w))
        self.assertLessEqual(day, set(self.w["yesterday"]))
        self.assertLessEqual(day, set(self.w["days"][0]))
        self.assertLessEqual({"time", "temp_f", "precip_chance", "precip_in", "icon"}, set(self.w["hours"][0]))

    def test_uk_means_great_britain(self):
        london = {"results": [{"name": "London", "admin1": "Ontario", "country": "Canada", "country_code": "CA", "latitude": 1, "longitude": 1},
                              {"name": "London", "admin1": "England", "country": "United Kingdom", "country_code": "GB", "latitude": 2, "longitude": 2}]}
        with mock.patch.object(weather, "_get", return_value=london):
            self.assertEqual(weather.geocode("London, UK")[0], "London, England, United Kingdom")

    def test_a_state_abbreviation_picks_the_right_town(self):
        with mock.patch.object(weather, "_get", return_value=BURLINGTONS):
            self.assertEqual(weather.geocode("Burlington, VT")[0], "Burlington, Vermont, United States")

    def test_a_country_code_also_matches(self):
        # "CA" is California as a state and Canada as a country.
        with mock.patch.object(weather, "_get", return_value=BURLINGTONS):
            self.assertEqual(weather.geocode("Burlington, CA")[0], "Burlington, Ontario, Canada")

    def test_an_unknown_place_says_so(self):
        with mock.patch.object(weather, "_get", return_value={}):
            with self.assertRaisesRegex(weather.WeatherError, "no place called"):
                weather.geocode("Nowhere")


if __name__ == "__main__":
    unittest.main()
