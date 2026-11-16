"""next-tickets.py: bucket sorting against stubbed `gh issue list` JSON."""

from __future__ import annotations

import unittest

from _loader import load

nt = load("next-tickets.py")


def issue(n, labels=(), state="OPEN", body=""):
    return {"number": n, "state": state, "title": f"t{n}", "body": body,
            "labels": [{"name": x} for x in ("q", *labels)]}


class NextTickets(unittest.TestCase):
    def buckets(self, issues):
        out = nt.classify(issues, ["q"], ["needs-greg", "manual"], "ready-for-agent")
        return {b: [r["number"] for r in rows] for b, rows in out.items()}

    def test_dependency_line_forms(self):
        self.assertEqual(nt.deps_of({"body": "Depends on: #3, #4 for the draw"}), [3, 4])
        self.assertEqual(nt.deps_of({"body": "x. depends on #5"}), [5])
        self.assertEqual(nt.deps_of({"body": "Depends on: none"}), [])

    def test_dependency_stops_at_first_sentence(self):
        body = ("Depends on: #32, #25 (pickups), #27 (thrown weapons). "
                "It can run beside #34; both touch the entity list.")
        self.assertEqual(nt.deps_of({"body": body}), [25, 27, 32])
        self.assertEqual(nt.deps_of({"body": "Depends on: #37 for the draw; the rest can land first."}), [37])
        self.assertEqual(nt.deps_of({"body": "Depends on: none."}), [])
        self.assertEqual(nt.deps_of({"body": "Depends on: #8 (see v1.2 notes)."}), [8])

    def test_buckets(self):
        got = self.buckets([
            issue(1, ["stage:building"]),
            issue(2, ["stage:reviewing"]),
            issue(3),
            issue(4, ["ready-for-agent", "priority:high"], body="Depends on: #9"),
            issue(5, ["ready-for-agent", "manual"]),
            issue(6, ["ready-for-agent"], body="Depends on: #1"),
            issue(7, ["ready-for-agent"], body="Depends on: #2"),
            issue(9, [], state="CLOSED"),
        ])
        self.assertEqual(got["in_flight"], [1, 2])
        self.assertEqual(got["unreadied"], [3])
        self.assertEqual(got["ready"], [4])
        self.assertEqual(got["held"], [5])
        self.assertEqual(got["blocked"], [6])
        self.assertEqual(got["can_start"], [7])

    def test_ready_sorts_by_priority_then_unblocks(self):
        got = self.buckets([
            issue(1, ["ready-for-agent", "priority:2"]),
            issue(2, ["ready-for-agent", "priority:2"]),
            issue(3, ["ready-for-agent", "priority:low"]),
            issue(4, ["priority:2"], body="Depends on: #2"),
            issue(5, ["ready-for-agent", "priority:0"]),
        ])
        self.assertEqual(got["ready"], [5, 2, 1, 3])

    def test_no_priority_flagged_last(self):
        out = nt.classify([issue(1, ["ready-for-agent"])], ["q"], [], "ready-for-agent")
        self.assertIn("NO PRIORITY LABEL", out["ready"][0]["notes"])

    def test_unprioritised_sorts_last_and_warns(self):
        issues = [issue(1, ["ready-for-agent"]), issue(2, ["ready-for-agent", "priority:3"]),
                  issue(3, ["ready-for-agent"])]
        out = nt.classify(issues, ["q"], [], "ready-for-agent")
        self.assertEqual([r["number"] for r in out["ready"]], [2, 1, 3])
        text = nt.render(out).splitlines()
        self.assertEqual(text[0], "2 tickets have no priority label: #1 #3")
        self.assertTrue(any(l.startswith("#1") and " P? " in l for l in text))


if __name__ == "__main__":
    unittest.main()
