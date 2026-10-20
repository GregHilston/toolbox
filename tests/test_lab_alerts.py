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
        out = la.pair([row(5, "nfs", "alert", "NFS down"), row(3, "nfs", "alert", "NFS still down (120m)")], NOW, 3)
        self.assertEqual((len(out), out[0]["repeats"], out[0]["title"], out[0]["end"]), (1, 2, "NFS still down (120m)", None))

    def test_keyed_clear_leaves_other_keys_open(self):
        rows = [row(4, "g", "alert", "a", "k1"), row(4, "g", "alert", "b", "k2"), row(1, "g", "clear", "a", "k1")]
        open_ = [i["title"] for i in la.pair(rows, NOW, 3) if i["end"] is None]
        self.assertEqual(open_, ["b"])

    def test_clear_matches_title_after_stripping_suffixes(self):
        rows = [row(5, "nfs", "alert", "dungeon: NFS down (no_ping)"),
                row(4, "nfs", "alert", "dungeon: NFS still down (364m)"),
                row(1, "nfs", "clear", "dungeon: NFS down")]
        out = la.pair(rows, NOW, 3)
        self.assertEqual((len(out), out[0]["repeats"], out[0]["end"] is not None), (1, 2, True))

    def test_other_fault_of_same_source_stays_open(self):
        rows = [row(5, "nfs", "alert", "NFS down"), row(4, "nfs", "alert", "OrbStack broken"),
                row(1, "nfs", "clear", "NFS down")]
        open_ = [i for i in la.pair(rows, NOW, 3) if i["end"] is None]
        self.assertEqual([i["title"] for i in open_], ["OrbStack broken"])

    def test_unmatched_clear_annotates_open_incident(self):
        rows = [row(5, "nfs", "alert", "OrbStack broken"), row(1, "nfs", "clear", "NFS down")]
        i = la.pair(rows, NOW, 3)[0]
        self.assertIsNone(i["end"])
        self.assertIn("did not name this", la.fmt_incident(i, NOW))

    def test_old_closed_incident_leaves_the_window(self):
        rows = [row(100, "w", "alert", "a"), row(99, "w", "clear", "a")]
        self.assertEqual(la.pair(rows, NOW, 3), [])

    def test_old_open_incident_stays(self):
        self.assertEqual(len(la.pair([row(100, "w", "alert", "a")], NOW, 3)), 1)

    def test_open_incident_older_than_a_week_stays(self):
        self.assertEqual(len(la.pair([row(24 * 9, "w", "alert", "a")], NOW, 3)), 1)

    def test_days_beyond_a_week_shows_older_closed_incident(self):
        rows = [row(24 * 9, "w", "alert", "a"), row(24 * 9 - 1, "w", "clear", "a")]
        self.assertEqual(len(la.pair(rows, NOW, 10)), 1)

    def test_info_stands_alone(self):
        out = la.pair([row(1, "g", "info", "healed")], NOW, 3)
        self.assertEqual(out[0]["kind"], "info")


class TestParse(unittest.TestCase):
    def test_bad_lines_are_skipped(self):
        self.assertIsNone(la.parse_row("not json"))
        self.assertIsNone(la.parse_row(json.dumps({"ts": "bad"})))

    def test_fractional_seconds_parse(self):
        self.assertIsNotNone(la.parse_row(json.dumps({"ts": "2026-10-20T03:32:42.123-0400", "kind": "alert"})))

    def test_ts_with_offset_parses(self):
        r = la.parse_row(json.dumps({"ts": "2026-10-20T03:32:42-0400", "kind": "alert"}))
        self.assertEqual(r["at"].utcoffset(), timedelta(hours=-4))


class TestFormat(unittest.TestCase):
    def test_open_line_says_no_clear(self):
        i = la.pair([row(5, "backup", "alert", "failed")], NOW, 3)[0]
        self.assertIn("OPEN", la.fmt_incident(i, NOW))
        self.assertIn("no clear yet", la.fmt_incident(i, NOW))

    def test_age(self):
        self.assertEqual([la.age(timedelta(minutes=m)) for m in (5, 120, 1500, 4000)], ["5m", "2h", "1d", "2d"])


if __name__ == "__main__":
    unittest.main()
