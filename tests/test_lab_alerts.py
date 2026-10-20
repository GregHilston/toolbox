"""lab-alerts pairs alerts with clears; no network."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
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

    def test_open_line_names_its_log(self):
        i = la.pair([row(5, "backup-offsite", "alert", "failed")], NOW, 3)[0]
        self.assertIn("log: ssh dungeon tail -n 50 ~/Library/Logs/backup-offsite.log", la.fmt_incident(i, NOW))

    def test_closed_line_has_no_log(self):
        i = la.pair([row(5, "backup", "alert", "failed"), row(1, "backup", "clear", "failed")], NOW, 3)[0]
        self.assertNotIn("log:", la.fmt_incident(i, NOW))

    def test_age(self):
        self.assertEqual([la.age(timedelta(minutes=m)) for m in (5, 120, 1500, 4000)], ["5m", "2h", "1d", "2d"])


def alert(name: str, mins_ago: int = 60, flag: str = "", **labels) -> dict:
    return {"name": name, "summary": "", "labels": labels, "flag": flag,
            "since": (NOW - timedelta(minutes=mins_ago)).isoformat()}


def rule(**kw) -> dict:
    return {"alert": kw.pop("alert"), "labels": kw}


def root(rid: str, down: dict, *explains: dict) -> dict:
    return {"id": rid, "down": down, "explains": list(explains)}


UNRAID = root("unraid", rule(alert=r"Service down \(standard\)", instance=r"^https://unraid\."),
              rule(alert=r"Service down \((critical|standard)\)", instance=r"^https://(sonarr|plex)\."),
              rule(alert="UPS telemetry lost"))
GLUETUN = root("gluetun", rule(alert="VPN-routed container missing"),
               rule(alert=r"Service down \(critical\)", instance=r"^https://sonarr\."))
UNRAID_DOWN = alert("Service down (standard)", instance="https://unraid.grehg2.xyz/login")
SONARR = alert("Service down (critical)", instance="https://sonarr.grehg2.xyz/ping")


class TestSharedCause(unittest.TestCase):
    def test_groups_dependents_when_root_is_down(self):
        got = la.shared_causes([UNRAID_DOWN, alert("UPS telemetry lost"), SONARR], [UNRAID])
        self.assertEqual(got["groups"][0]["explains"], ["UPS telemetry lost", "sonarr"])
        self.assertEqual(got["unexplained"], [])

    def test_no_root_down_means_no_grouping(self):
        self.assertEqual(la.shared_causes([alert("UPS telemetry lost")], [UNRAID]), {})

    def test_undeclared_alerts_say_which_one(self):
        got = la.shared_causes([UNRAID_DOWN, alert("Battery-backed AP down"),
                                alert("Unraid disk failing", disk="parity")], [UNRAID])
        self.assertEqual(got["unexplained"], ["Battery-backed AP down", "Unraid disk failing (parity)"])

    def test_label_regex_must_match(self):
        roam = alert("Service down (critical)", instance="https://roger.grehg2.xyz/")
        got = la.shared_causes([UNRAID_DOWN, roam], [UNRAID])
        self.assertEqual((got["groups"][0]["explains"], got["unexplained"]), ([], ["Service down (critical) (roger)"]))

    def test_alert_for_two_roots_prints_once_as_shared(self):
        got = la.shared_causes([UNRAID_DOWN, alert("VPN-routed container missing"), SONARR], [UNRAID, GLUETUN])
        self.assertEqual([g["explains"] for g in got["groups"]], [[], []])
        self.assertEqual(got["shared"], [{"roots": ["unraid", "gluetun"], "explains": ["sonarr"]}])

    def test_alert_older_than_root_is_not_explained(self):
        old = alert("UPS telemetry lost", mins_ago=60 * 24 * 8)
        got = la.shared_causes([UNRAID_DOWN, old], [UNRAID])
        self.assertEqual((got["groups"][0]["explains"], got["unexplained"]), ([], ["UPS telemetry lost"]))

    def test_alert_just_before_root_still_counts(self):
        early = alert("UPS telemetry lost", mins_ago=65)
        got = la.shared_causes([alert("Service down (standard)", mins_ago=60, instance="https://unraid.x/"), early], [UNRAID])
        self.assertEqual(got["groups"][0]["explains"], ["UPS telemetry lost"])

    def test_silenced_root_forms_no_group(self):
        got = la.shared_causes([alert(UNRAID_DOWN["name"], flag="silenced", **UNRAID_DOWN["labels"]),
                                alert("UPS telemetry lost")], [UNRAID])
        self.assertEqual(got, {})

    def test_duplicates_keep_a_count(self):
        got = la.shared_causes([UNRAID_DOWN, alert("UPS telemetry lost"), alert("UPS telemetry lost")], [UNRAID])
        self.assertEqual(got["groups"][0]["explains"], ["UPS telemetry lost x2"])


class TestLoadDeps(unittest.TestCase):
    def write(self, text: str) -> str:
        f = tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False)
        self.addCleanup(os.unlink, f.name)
        f.write(text)
        f.close()
        return f.name

    def test_missing_file_is_silent(self):
        self.assertEqual(la.load_deps("/nonexistent/deps.toml"), ([], ""))

    def test_unparsable_file_warns(self):
        roots, warn = la.load_deps(self.write("[[root"))
        self.assertEqual(roots, [])
        self.assertIn("unreadable", warn)

    def test_bad_regex_warns(self):
        roots, warn = la.load_deps(self.write('[[root]]\nid="x"\ndown={alert="(", }\n'))
        self.assertEqual(roots, [])
        self.assertIn("invalid", warn)

    def test_missing_down_warns(self):
        self.assertIn("invalid", la.load_deps(self.write('[[root]]\nid="x"\n'))[1])

    def test_shipped_map_compiles_and_has_citations(self):
        path = Path("~/Git/home-lab/ops/dependencies.toml").expanduser()
        if not path.exists():
            self.skipTest("home-lab map not present")
        roots, warn = la.load_deps(str(path))
        self.assertEqual(warn, "")
        self.assertGreater(len(roots), 0)
        for r in roots:
            self.assertTrue(r["explains"], r["id"])


if __name__ == "__main__":
    unittest.main()
