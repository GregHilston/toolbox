"""ticket-lanes.py: stage intervals and drift from fixture timelines."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from _loader import load

tl = load("ticket-lanes.py")

T0 = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
NOW = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)


def at(minutes):
    return (T0 + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def ev(kind, minutes, label=None):
    e = {"event": kind, "created_at": at(minutes)}
    if label:
        e["label"] = {"name": label}
    return e


def ticket(events, closed=None):
    return {"number": 1, "closed_at": at(closed) if closed is not None else None,
            "events": events}


def stats(t):
    return tl.ticket_stats(t["events"], tl.parse(t["closed_at"]) if t["closed_at"] else None, NOW)


class Stats(unittest.TestCase):
    def test_plain_ticket(self):
        s = stats(ticket([ev("labeled", 0, "stage:building"), ev("unlabeled", 18, "stage:building"),
                          ev("labeled", 18, "stage:reviewing"), ev("unlabeled", 30, "stage:reviewing"),
                          ev("closed", 42)], closed=42))
        self.assertEqual(s["stage:building"], (18 * 60, 1))
        self.assertEqual(s["stage:reviewing"], (12 * 60, 1))
        self.assertEqual(s["unlabeled"], (12 * 60, 1))

    def test_two_fixing_rounds(self):
        s = stats(ticket([ev("labeled", 0, "stage:fixing"), ev("unlabeled", 10, "stage:fixing"),
                          ev("labeled", 20, "stage:fixing"), ev("unlabeled", 25, "stage:fixing"),
                          ev("closed", 30)], closed=30))
        self.assertEqual(s["stage:fixing"], (15 * 60, 2))

    def test_label_left_on_runs_to_close(self):
        s = stats(ticket([ev("labeled", 0, "stage:landing"), ev("closed", 7)], closed=7))
        self.assertEqual(s["stage:landing"], (7 * 60, 1))
        self.assertNotIn("unlabeled", s)

    def test_open_ticket_runs_to_now(self):
        s = stats(ticket([ev("labeled", 0, "stage:building")]))
        self.assertEqual(s["stage:building"][0], int((NOW - T0).total_seconds()))

    def test_no_stage_labels(self):
        s = stats(ticket([ev("labeled", 0, "bug"), ev("closed", 5)], closed=5))
        self.assertEqual(s, {})


def tickets(stage, durations, closed_days_ago):
    out = []
    for i, d in enumerate(durations):
        end = NOW - timedelta(days=closed_days_ago, hours=i)
        start = end - timedelta(minutes=d)
        out.append({"number": i, "closed_at": end,
                    "stats": {stage: (d * 60, 1)}})
    return out


class Drift(unittest.TestCase):
    def lines(self, rows, **kw):
        return tl.drift_lines(rows, NOW, **kw)

    def test_rise_speaks(self):
        rows = tickets("stage:building", [40] * 5, 2) + tickets("stage:building", [20] * 5, 10)
        out = self.lines(rows)
        self.assertEqual(len(out), 1)
        self.assertIn("stage:building", out[0])

    def test_small_rise_silent(self):
        rows = tickets("stage:building", [12] * 5, 2) + tickets("stage:building", [6] * 5, 10)
        self.assertEqual(self.lines(rows), [])

    def test_below_min_sample_silent(self):
        rows = tickets("stage:building", [90] * 4, 2) + tickets("stage:building", [20] * 5, 10)
        self.assertEqual(self.lines(rows), [])

    def test_flat_silent(self):
        rows = tickets("stage:building", [30] * 5, 2) + tickets("stage:building", [30] * 5, 10)
        self.assertEqual(self.lines(rows), [])


class Quota(unittest.TestCase):
    def run_with(self, remaining, calls):
        real = tl.gh
        tl.gh = lambda *a: '{"resources": {"core": {"remaining": %d, "reset": 0}}}' % remaining
        try:
            tl.check_quota(calls)
        finally:
            tl.gh = real

    def test_refuses_under_reserve(self):
        with self.assertRaises(SystemExit) as stop:
            self.run_with(1800, 400)
        self.assertEqual(stop.exception.code, 2)

    def test_runs_with_room(self):
        self.run_with(5000, 400)


if __name__ == "__main__":
    unittest.main()
