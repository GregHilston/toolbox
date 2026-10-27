"""room-temps.py picks rooms, reads times and marks, and finds setpoint changes."""

from __future__ import annotations

import unittest
from datetime import date, datetime

from _loader import load

rt = load("room-temps.py")
TODAY = date(2026, 10, 27)


class PickRoomsTest(unittest.TestCase):
    def test_substring_matches_one_room(self):
        self.assertEqual([r.name for r in rt.pick_rooms(["guest", "BASE"])], ["Guest room", "Basement"])

    def test_room_without_data_is_refused(self):
        with self.assertRaises(ValueError):
            rt.pick_rooms(["living"])

    def test_ambiguous_name_is_refused(self):
        with self.assertRaises(ValueError):
            rt.pick_rooms(["room"])


class WhenTest(unittest.TestCase):
    def test_clock_time_is_today(self):
        self.assertEqual(rt.parse_when("07:10", TODAY), datetime(2026, 10, 27, 7, 10, tzinfo=rt.TZ))

    def test_iso_datetime_is_eastern(self):
        self.assertEqual(rt.parse_when("2026-10-20 06:00", TODAY), datetime(2026, 10, 20, 6, tzinfo=rt.TZ))

    def test_am_pm_and_short_hours(self):
        self.assertEqual(rt.parse_when("7am", TODAY).hour, 7)
        self.assertEqual(rt.parse_when("7:10pm", TODAY).hour, 19)
        self.assertEqual(rt.parse_when("12am", TODAY).hour, 0)
        self.assertEqual(rt.parse_when("6:05", TODAY).minute, 5)

    def test_bad_time_names_the_forms(self):
        with self.assertRaisesRegex(ValueError, "7am"):
            rt.parse_when("seven", TODAY)


class WindowTest(unittest.TestCase):
    NOW = datetime(2026, 10, 27, 8, 30, tzinfo=rt.TZ)

    def test_window_across_midnight_starts_yesterday(self):
        start, end = rt.window("22:00", "02:00", self.NOW)
        self.assertEqual((start.day, end.day), (26, 27))

    def test_start_after_now_means_yesterday(self):
        start, _ = rt.window("09:00", None, self.NOW)
        self.assertEqual(start.day, 26)

    def test_reversed_iso_window_is_refused(self):
        with self.assertRaises(ValueError):
            rt.window("2026-10-27 09:00", "2026-10-27 08:00", self.NOW)


class MarkTest(unittest.TestCase):
    START = datetime(2026, 10, 26, 22, 0, tzinfo=rt.TZ)

    def test_needs_a_label(self):
        with self.assertRaises(ValueError):
            rt.parse_mark("07:10", self.START)
        self.assertEqual(rt.parse_mark("07:10 = Heads on", self.START).label, "Heads on")

    def test_clock_mark_after_midnight_rolls_forward(self):
        self.assertEqual(rt.parse_mark("1:00=x", self.START).at.day, 27)

    def test_rooms_before_at_limit_a_mark(self):
        m = rt.parse_mark("guest,dining@~7:09=Head on", self.START)
        self.assertEqual(m.rooms, ("Guest room", "Dining room"))
        self.assertTrue(m.estimated)
        self.assertEqual(rt.parse_mark("7:09=x", self.START).rooms, ())

    def test_tilde_is_an_estimate(self):
        m = rt.parse_mark("~23:10=Head on", self.START)
        self.assertTrue(m.estimated)
        self.assertEqual(m.at.hour, 23)


class SummaryTest(unittest.TestCase):
    def test_a_stall_is_named_even_after_recovery(self):
        t0 = datetime(2026, 10, 27, 7, 0, tzinfo=rt.TZ).timestamp()
        pts = [(t0, 61.0), (t0 + 3600, 65.5), (t0 + 7200, 64.0), (t0 + 10800, 69.0)]
        self.assertEqual(rt.summary(pts), "low 61.0 at 7:00, fell 65.5→64.0 from 8:00 to 9:00, now 69.0 °F")

    def test_small_wobbles_are_not_a_fall(self):
        t0 = datetime(2026, 10, 27, 7, 0, tzinfo=rt.TZ).timestamp()
        self.assertEqual(rt.summary([(t0, 64.0), (t0 + 60, 64.5), (t0 + 120, 64.0)]), "low 64.0 at 7:00, now 64.0 °F")


class PlotTest(unittest.TestCase):
    def test_renders_with_empty_room_and_no_outdoor(self):
        import tempfile
        from pathlib import Path

        start = datetime(2026, 10, 27, 6, 0, tzinfo=rt.TZ)
        end = datetime(2026, 10, 27, 9, 0, tzinfo=rt.TZ)
        picked = rt.pick_rooms(["guest", "dining"])
        t = start.timestamp()
        data = {
            "temps": {"Guest room": [(t, 64.0), (t + 600, 66.0)], "Dining room": []},
            "targets": {"climate.1st_floor_thermostat": [(t, 66.0), (t + 600, 62.0)]},
            "zones": {"1st floor zone": {"spans": [(t, t + 300)], "setpoints": [(t + 600, 66.0, 62.0)]},
                      "2nd floor zone": {"spans": [], "setpoints": []}},
            "outdoor": [],
        }
        marks = [rt.Mark(start, "on"), rt.Mark(start, "guess", estimated=True), rt.Mark(start, "here", rooms=("Guest room",))]
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "c.png"
            rt.plot(data, picked, marks, start, end, True, out)
            self.assertGreater(out.stat().st_size, 1000)


class SetpointTest(unittest.TestCase):
    def test_only_changes_are_reported(self):
        points = [(0, 66.0), (60, 66.0), (120, 62.0), (180, 62.0)]
        self.assertEqual(rt.setpoint_changes(points), [(120, 66.0, 62.0)])


if __name__ == "__main__":
    unittest.main()
