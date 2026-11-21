"""ticket-lanes.py: stage intervals, flow metrics and drift from fixture timelines."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from _loader import load

tl = load("ticket-lanes.py")

NOW = datetime.now(timezone.utc).replace(microsecond=0)
T0 = NOW - timedelta(days=10)


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
    def run_with(self, remaining):
        real = tl.gh
        tl.gh = lambda *a: '{"resources": {"graphql": {"remaining": %d, "reset": 0}}}' % remaining
        try:
            tl.check_quota()
        finally:
            tl.gh = real

    def test_refuses_under_reserve(self):
        with self.assertRaises(SystemExit) as stop:
            self.run_with(499)
        self.assertEqual(stop.exception.code, 2)

    def test_runs_with_room(self):
        self.run_with(500)


def row(events, closed=None, number=1):
    c = tl.parse(at(closed)) if closed is not None else None
    return tl.make_row(number, T0, c, events, NOW)


def lab(stage, start, end):
    return [ev("labeled", start, "stage:" + stage), ev("unlabeled", end, "stage:" + stage)]


def when(m):
    return T0 + timedelta(minutes=m)


class Windows(unittest.TestCase):
    def test_parse_when_date_and_zone(self):
        self.assertEqual(tl.parse_when("2026-11-20T07:00+00:00"),
                         datetime(2026, 11, 20, 7, tzinfo=timezone.utc))
        self.assertEqual(tl.parse_when("2026-11-20").tzinfo, timezone.utc)

    def test_split_repo(self):
        self.assertEqual(tl.split_repo("gridkeep"), ("GregHilston", "gridkeep"))
        self.assertEqual(tl.split_repo("o/r"), ("o", "r"))

    def test_in_window_by_close(self):
        r = row(lab("building", 0, 10) + [ev("closed", 10)], closed=10)
        self.assertTrue(tl.in_window(r, when(0), when(11), False))
        self.assertFalse(tl.in_window(r, when(0), when(10), False))
        self.assertFalse(tl.in_window(row(lab("building", 0, 5)), when(0), when(60), False))
        self.assertTrue(tl.in_window(row(lab("building", 0, 5)), when(0), when(60), True))


class Throughput(unittest.TestCase):
    def test_rate_and_buckets(self):
        rows = [row([], closed=m, number=m) for m in (10, 20, 130)]
        t = tl.throughput(rows, when(0), when(240), 2)
        self.assertEqual(t["closed"], 3)
        self.assertAlmostEqual(t["per_hour"], 0.75)
        self.assertEqual([b["closed"] for b in t["buckets"]], [2, 1])

    def test_stall_shows_zero_bucket(self):
        t = tl.throughput([row([], closed=10)], when(0), when(360), 2)
        self.assertEqual([b["closed"] for b in t["buckets"]], [1, 0, 0])


class Lead(unittest.TestCase):
    def test_lead_and_unstaged_gap(self):
        ev_ = lab("building", 10, 20) + lab("reviewing", 30, 40) + [ev("closed", 60)]
        lt = tl.lead_times([row(ev_, closed=60)])
        self.assertEqual(lt["lead_median_min"], 50)
        self.assertEqual(lt["staged_median_min"], 20)
        self.assertEqual(lt["no_stage_median_min"], 30)

    def test_unstaged_ticket_skipped(self):
        self.assertEqual(tl.lead_times([row([ev("closed", 5)], closed=5)]), {"tickets": 0})


class Flow(unittest.TestCase):
    def test_efficiency_counts_active_stages_only(self):
        ev_ = lab("building", 0, 10) + lab("reviewing", 10, 40) + lab("fixing", 40, 50) + [ev("closed", 50)]
        fe = tl.flow_efficiency([row(ev_, closed=50)], {"building", "fixing"})
        self.assertAlmostEqual(fe["efficiency"], 20 / 50)

    def test_custom_active_set(self):
        ev_ = lab("building", 0, 10) + lab("reviewing", 10, 40) + [ev("closed", 40)]
        fe = tl.flow_efficiency([row(ev_, closed=40)], {"reviewing"})
        self.assertAlmostEqual(fe["efficiency"], 30 / 40)

    def test_overlap_not_double_counted(self):
        ev_ = lab("building", 0, 20) + lab("fixing", 10, 30) + [ev("closed", 30)]
        fe = tl.flow_efficiency([row(ev_, closed=30)], {"building", "fixing"})
        self.assertAlmostEqual(fe["efficiency"], 1.0)


class Rework(unittest.TestCase):
    def test_share_and_rounds(self):
        a = row(lab("building", 0, 5) + lab("fixing", 5, 8) + lab("fixing", 9, 12), closed=12)
        b = row(lab("building", 0, 5), closed=5)
        rw = tl.rework([a, b])
        self.assertEqual(rw["share"], 0.5)
        self.assertEqual(rw["rounds_per_ticket"], 1.0)
        self.assertEqual(rw["rounds_per_fixed_ticket"], 2.0)


class Wip(unittest.TestCase):
    def test_max_and_mean(self):
        a = row(lab("building", 0, 40), closed=40, number=1)
        b = row(lab("building", 20, 60), closed=60, number=2)
        w = tl.wip([a, b], when(0), when(60))["stage:building"]
        self.assertEqual(w["max"], 2)
        self.assertAlmostEqual(w["mean"], 80 / 60)

    def test_clipped_to_window(self):
        a = row(lab("building", 0, 100), closed=100)
        w = tl.wip([a], when(40), when(60))["stage:building"]
        self.assertAlmostEqual(w["mean"], 1.0)


class Quality(unittest.TestCase):
    def test_overlap_and_left_on(self):
        a = row([ev("labeled", 0, "stage:building"), ev("labeled", 5, "stage:reviewing"),
                 ev("closed", 9)], closed=9)
        q = tl.quality([a, row(lab("building", 0, 5), closed=9)])
        self.assertEqual(q, {"overlapping_stage_labels": 1, "closed_with_stage_label": 1})


class Prefix(unittest.TestCase):
    def test_custom_prefix(self):
        evs = [{"event": "labeled", "created_at": at(0), "label": {"name": "lane:a"}},
               {"event": "unlabeled", "created_at": at(5), "label": {"name": "lane:a"}}]
        s = tl.ticket_stats(evs, tl.parse(at(5)), NOW, "lane:")
        self.assertEqual(s["lane:a"], (300, 1))


class FakeGraphQL(unittest.TestCase):
    def node(self, number, closed_min, events, more=False):
        return {"id": f"I{number}", "number": number, "closedAt": at(closed_min),
                "createdAt": at(0),
                "timelineItems": {"pageInfo": {"hasNextPage": more, "endCursor": "c"},
                                  "nodes": events}}

    def labeled(self, kind, m, name):
        return {"__typename": kind, "createdAt": at(m), "label": {"name": name}}

    def run_fetch(self, pages, extra=None):
        calls, served = [], []

        def fake(query, **v):
            calls.append(v)
            if "node(id" in query:
                return {"rateLimit": {"cost": 1, "remaining": 4000}, "node": {"timelineItems": extra}}
            served.append(1)
            return {"rateLimit": {"cost": 2, "remaining": 4000},
                    "repository": {"issues": pages[len(served) - 1]}}
        real_g, real_q = tl.graphql, tl.check_quota
        tl.graphql, tl.check_quota = fake, lambda *a: None
        try:
            return tl.fetch("o", "r", when(0), False, NOW), calls
        finally:
            tl.graphql, tl.check_quota = real_g, real_q

    def test_pages_issues_and_timeline(self):
        n1 = self.node(1, 30, [self.labeled("LabeledEvent", 0, "stage:building")], more=True)
        n2 = self.node(2, 20, [self.labeled("LabeledEvent", 0, "stage:building"),
                               self.labeled("UnlabeledEvent", 20, "stage:building")])
        pages = [{"pageInfo": {"hasNextPage": True, "endCursor": "p"}, "nodes": [n1]},
                 {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": [n2]}]
        extra = {"pageInfo": {"hasNextPage": False, "endCursor": None},
                 "nodes": [self.labeled("UnlabeledEvent", 30, "stage:building")]}
        rows, calls = self.run_fetch(pages, extra)
        self.assertEqual([r["number"] for r in rows], [1, 2])
        self.assertEqual(rows[0]["stats"]["stage:building"], (30 * 60, 1))
        self.assertEqual(calls[1]["after"], "c")
        self.assertEqual(calls[2]["after"], "p")


if __name__ == "__main__":
    unittest.main()
