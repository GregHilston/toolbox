"""lab-alerts pairs alerts with clears; no network."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone

from _loader import load

la = load("lab-alerts.py")

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)


def row(hours_ago: float, source: str, kind: str, title: str, key: str | None = None) -> dict:
    r = {"ts": "x", "at": NOW - timedelta(hours=hours_ago), "source": source, "kind": kind, "title": title}
    if key:
        r["key"] = key
    return r


class TestPair(unittest.TestCase):
    def test_clear_closes_its_alert(self):
        out = la.pair([row(3, "nfs", "alert", "NFS down"), row(2, "nfs", "clear", "NFS down")], NOW, 3)
        self.assertEqual([(i["end"] is not None) for i in out], [True])

    def test_repeats_merge_and_stay_open(self):
        out = la.pair([row(5, "nfs", "alert", "down"), row(3, "nfs", "alert", "still down (120m)")], NOW, 3)
        self.assertEqual((len(out), out[0]["repeats"], out[0]["title"], out[0]["end"]), (1, 2, "still down (120m)", None))

    def test_keyed_clear_leaves_other_keys_open(self):
        rows = [row(4, "g", "alert", "a", "k1"), row(4, "g", "alert", "b", "k2"), row(1, "g", "clear", "a", "k1")]
        open_ = [i["title"] for i in la.pair(rows, NOW, 3) if i["end"] is None]
        self.assertEqual(open_, ["b"])

    def test_keyless_clear_closes_the_whole_source(self):
        rows = [row(4, "w", "alert", "a"), row(1, "w", "clear", "a")]
        self.assertTrue(all(i["end"] for i in la.pair(rows, NOW, 3)))

    def test_old_closed_incident_leaves_the_window(self):
        rows = [row(100, "w", "alert", "a"), row(99, "w", "clear", "a")]
        self.assertEqual(la.pair(rows, NOW, 3), [])

    def test_old_open_incident_stays(self):
        self.assertEqual(len(la.pair([row(100, "w", "alert", "a")], NOW, 3)), 1)

    def test_info_stands_alone(self):
        out = la.pair([row(1, "g", "info", "healed")], NOW, 3)
        self.assertEqual(out[0]["kind"], "info")


class TestParse(unittest.TestCase):
    def test_bad_lines_are_skipped(self):
        self.assertIsNone(la.parse_row("not json"))
        self.assertIsNone(la.parse_row(json.dumps({"ts": "bad"})))

    def test_ts_with_offset_parses(self):
        r = la.parse_row(json.dumps({"ts": "2026-10-20T03:32:42-0400", "kind": "alert"}))
        self.assertEqual(r["at"].utcoffset(), timedelta(hours=-4))


class TestFormat(unittest.TestCase):
    def test_open_line_says_no_clear(self):
        i = la.pair([row(5, "backup", "alert", "failed")], NOW, 3)[0]
        self.assertIn("OPEN", la.fmt_incident(i, NOW))
        self.assertIn("no clear yet", la.fmt_incident(i, NOW))

    def test_age(self):
        self.assertEqual([la.age(timedelta(minutes=m)) for m in (5, 120, 4000)], ["5m", "2h", "2d"])


if __name__ == "__main__":
    unittest.main()
