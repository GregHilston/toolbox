"""The preflight exists to catch two invisible states, so that is what these test.

Neither "the key is nearly empty" nor "peak opens in twenty minutes" shows up
anywhere until the bill does, and the second is genuinely easy to get wrong: the
peak windows are defined in UTC and the person starting the run is in Eastern,
where a Sunday evening is already Monday in UTC.

Everything here drives `evaluate` and the two clock helpers directly. Nothing
touches the network or the real clock.
"""

from __future__ import annotations

import datetime as dt
import unittest

from _loader import load

pf = load("deepseek-preflight.py")


def utc(y, m, d, h, mi=0):
    return dt.datetime(y, m, d, h, mi, tzinfo=dt.timezone.utc)


class TestPeakWindows(unittest.TestCase):
    def test_the_two_weekday_windows_are_peak(self):
        # 2026-08-27 is a Thursday.
        self.assertTrue(pf.is_peak(utc(2026, 8, 27, 1)), "01:00 opens the first window")
        self.assertTrue(pf.is_peak(utc(2026, 8, 27, 3, 59)), "03:59 is still in it")
        self.assertTrue(pf.is_peak(utc(2026, 8, 27, 6)), "06:00 opens the second")
        self.assertTrue(pf.is_peak(utc(2026, 8, 27, 9, 59)), "09:59 is still in it")

    def test_the_gaps_and_the_ends_are_not(self):
        self.assertFalse(pf.is_peak(utc(2026, 8, 27, 0, 59)), "a minute before is off-peak")
        self.assertFalse(pf.is_peak(utc(2026, 8, 27, 4)), "the end is exclusive")
        self.assertFalse(pf.is_peak(utc(2026, 8, 27, 5)), "the gap between windows")
        self.assertFalse(pf.is_peak(utc(2026, 8, 27, 10)), "and the end of the second")
        self.assertFalse(pf.is_peak(utc(2026, 8, 27, 20)), "the run this came from")

    def test_weekends_are_never_peak(self):
        # 2026-08-29 is a Saturday, 2026-08-30 a Sunday.
        self.assertFalse(pf.is_peak(utc(2026, 8, 29, 2)), "Saturday inside a window")
        self.assertFalse(pf.is_peak(utc(2026, 8, 30, 7)), "Sunday inside the other")

    def test_the_eastern_trap_the_windows_are_utc_weekdays(self):
        """21:00 Eastern on a Sunday is 01:00 UTC on Monday, and so it is peak.

        This is the case the whole script exists for: someone starts an
        overnight run after dinner and it bills at double.
        """
        sunday_evening_et = utc(2026, 8, 31, 1)  # Monday 01:00 UTC
        self.assertEqual(sunday_evening_et.weekday(), 0, "it is Monday in UTC")
        self.assertTrue(pf.is_peak(sunday_evening_et))


class TestMinutesUntilPeak(unittest.TestCase):
    def test_zero_while_inside_one(self):
        self.assertEqual(pf.minutes_until_peak(utc(2026, 8, 27, 2)), 0)

    def test_counts_forward_to_the_next_opening(self):
        self.assertEqual(pf.minutes_until_peak(utc(2026, 8, 27, 0, 30)), 30)
        self.assertEqual(pf.minutes_until_peak(utc(2026, 8, 27, 5, 30)), 30,
                         "the gap between the two windows counts to the second")

    def test_crosses_a_weekend_rather_than_giving_up(self):
        friday_evening = utc(2026, 8, 28, 22)
        mins = pf.minutes_until_peak(friday_evening)
        self.assertIsNotNone(mins)
        self.assertTrue(pf.is_peak(friday_evening + dt.timedelta(minutes=mins)))
        self.assertGreater(mins, 24 * 60, "the next window is Monday, not Saturday")


class TestEvaluate(unittest.TestCase):
    OFF = utc(2026, 8, 27, 20)  # Thursday afternoon Eastern; the measured run

    def test_clear_when_funded_and_off_peak(self):
        v = pf.evaluate(25.0, self.OFF, min_balance=2.0, warn_minutes=90)
        self.assertTrue(v["ok"])
        self.assertEqual(v["problems"], [])

    def test_a_low_balance_is_a_problem(self):
        v = pf.evaluate(1.5, self.OFF, min_balance=2.0, warn_minutes=90)
        self.assertFalse(v["ok"])
        self.assertIn("balance", v["problems"][0])

    def test_a_negative_balance_is_the_state_that_ended_the_real_run(self):
        v = pf.evaluate(-0.13, self.OFF, min_balance=2.0, warn_minutes=90)
        self.assertFalse(v["ok"])

    def test_being_in_peak_is_a_problem_even_when_rich(self):
        v = pf.evaluate(500.0, utc(2026, 8, 27, 2), min_balance=2.0, warn_minutes=90)
        self.assertFalse(v["ok"])
        self.assertTrue(v["peak_now"])
        self.assertIn("PEAK", v["problems"][0])

    def test_peak_soon_warns_without_being_in_it(self):
        v = pf.evaluate(500.0, utc(2026, 8, 27, 0, 30), min_balance=2.0, warn_minutes=90)
        self.assertFalse(v["ok"])
        self.assertFalse(v["peak_now"], "not in it yet")
        self.assertTrue(v["peak_soon"])
        self.assertIn("30 min", v["problems"][0])

    def test_peak_soon_respects_the_window(self):
        v = pf.evaluate(500.0, utc(2026, 8, 27, 0, 30), min_balance=2.0, warn_minutes=10)
        self.assertTrue(v["ok"], "30 minutes out is not soon when the window is 10")

    def test_both_problems_are_reported_not_just_the_first(self):
        v = pf.evaluate(0.0, utc(2026, 8, 27, 2), min_balance=2.0, warn_minutes=90)
        self.assertEqual(len(v["problems"]), 2, "a human wants to hear about both")

    def test_an_unknown_balance_does_not_invent_a_problem(self):
        v = pf.evaluate(None, self.OFF, min_balance=2.0, warn_minutes=90)
        self.assertTrue(v["ok"], "cannot-tell is not the same as too-low")


class TestPrices(unittest.TestCase):
    def test_peak_is_exactly_double_off_peak(self):
        for model, rates in pf.PRICES.items():
            for off, peak in zip(rates["off"], rates["peak"]):
                self.assertAlmostEqual(peak, off * 2, places=6, msg=model)

    def test_pro_is_three_times_flash(self):
        pro = pf.PRICES["deepseek-v4-pro"]["off"]
        flash = pf.PRICES["deepseek-v4-flash"]["off"]
        for p, f in zip(pro, flash):
            self.assertAlmostEqual(p / f, 3.0, delta=0.15,
                                   msg="the 3x gap is the whole Flash argument")


if __name__ == "__main__":
    unittest.main()
