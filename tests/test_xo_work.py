"""xo-work.py alerts on approved-unlanded tickets and idle slots beside ready P0s, and only then."""

from __future__ import annotations

import unittest

from _loader import load

xo = load("xo-work.py")


def issue(n, *labels, body="", last=None):
    return {"number": n, "labels": [{"name": x} for x in labels], "body": body,
            "comments": [{"body": last}] if last else []}


def run(issues, state=None, now=10_000.0, cap=6):
    return xo.check(issues, state or {}, now, cap, "lp")


class Approved(unittest.TestCase):
    def test_label_alerts_after_30_min(self):
        a, seen = run([issue(1, "stage:approved")])
        self.assertEqual(a, [])
        a, _ = run([issue(1, "stage:approved")], seen, now=10_000 + 1800)
        self.assertEqual(a, ["XO lp: #1 approved over 30 min, not landed"])

    def test_drain_comment_counts_while_label_says_reviewing(self):
        a, _ = run([issue(406, "stage:reviewing", last="drain: APPROVED (review + fix round done)")],
                   {"approved-406": 0.0})
        self.assertEqual(a, ["XO lp: #406 approved over 30 min, not landed"])

    def test_reviewing_without_verdict_is_quiet(self):
        a, _ = run([issue(5, "stage:reviewing", last="review started")], {"approved-5": 0.0})
        self.assertEqual(a, [])

    def test_landed_ticket_forgets_its_clock(self):
        _, seen = run([], {"approved-1": 0.0})
        self.assertNotIn("approved-1", seen)


class Slots(unittest.TestCase):
    ready = issue(430, "priority:0", "ready-for-agent")

    def test_free_slot_and_ready_p0_alerts_after_20_min(self):
        a, seen = run([self.ready, issue(1, "stage:building")])
        self.assertEqual(a, [])
        a, _ = run([self.ready, issue(1, "stage:building")], seen, now=10_000 + 1200)
        self.assertEqual(a, ["XO lp: 5 of 6 slots free beside ready P0s #430 for 20 min"])

    def test_full_slots_are_quiet(self):
        busy = [issue(i, "stage:building") for i in range(1, 7)]
        a, _ = run([self.ready, *busy], {"slots": 0.0})
        self.assertEqual(a, [])

    def test_blocked_by_an_open_ticket_is_not_ready(self):
        a, _ = run([issue(408, "priority:0", "ready-for-agent", body="Blocked by: #407."),
                    issue(407, "stage:reviewing")], {"slots": 0.0})
        self.assertEqual(a, [])

    def test_blocker_closed_makes_it_ready(self):
        a, _ = run([issue(408, "priority:0", "ready-for-agent", body="Depends on #402.")], {"slots": 0.0})
        self.assertEqual(a, ["XO lp: 6 of 6 slots free beside ready P0s #408 for 20 min"])

    def test_staged_or_needs_greg_p0_is_not_ready(self):
        a, _ = run([issue(1, "priority:0", "ready-for-agent", "stage:reviewing"),
                    issue(2, "priority:0", "ready-for-agent", "needs-greg"),
                    issue(3, "priority:1", "ready-for-agent")], {"slots": 0.0})
        self.assertEqual(a, [])


if __name__ == "__main__":
    unittest.main()
