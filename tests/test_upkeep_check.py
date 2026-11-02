"""The report's value is its verdicts, so these drive the pure functions.

Each case is a miss from the 2026-11-02 upkeep run: a quiet Dependabot, a host
that looked deployed, a busy Mac that a build would have competed with.
Nothing touches the network, `gh` or ssh.
"""

from __future__ import annotations

import unittest

from _loader import load

uk = load("upkeep-check.py")

DAY = 86400


class TestAudit(unittest.TestCase):
    def test_counts_only_high_and_critical_as_attention(self):
        moderate = {"metadata": {"vulnerabilities": {"moderate": 3, "total": 3}}, "vulnerabilities": {}}
        high = {"metadata": {"vulnerabilities": {"high": 1, "total": 1}}, "vulnerabilities": {}}
        self.assertFalse(uk.audit_needs_attention(moderate))
        self.assertTrue(uk.audit_needs_attention(high))

    def test_names_the_packages_that_carry_their_own_advisory(self):
        report = {
            "metadata": {"vulnerabilities": {"high": 1, "moderate": 1, "total": 2}},
            "vulnerabilities": {
                "undici": {"severity": "high", "via": [{"title": "x"}]},
                "pi-agent-suite": {"severity": "moderate", "via": ["undici"]},
            },
        }
        line = uk.audit_line("dot/pi/npm", report)
        self.assertIn("undici (high)", line)
        self.assertNotIn("pi-agent-suite", line)

    def test_a_clean_lockfile_reads_clean(self):
        clean = {"metadata": {"vulnerabilities": {"total": 0}}, "vulnerabilities": {}}
        self.assertIn("clean", uk.audit_line("x", clean))


class TestLock(unittest.TestCase):
    LOCK = {
        "root": "root",
        "nodes": {
            "root": {"inputs": {"nixpkgs": "nixpkgs", "darwin": "darwin"}},
            "nixpkgs": {"locked": {"rev": "6ad174a6d", "lastModified": 1000 * DAY}},
            "darwin": {"locked": {"rev": "ff0e21a41ffff"}},
        },
    }

    def test_age_comes_from_nixpkgs(self):
        self.assertEqual(uk.lock_age_days(self.LOCK, 1020 * DAY), 20)

    def test_age_follows_the_root_input_past_a_transitive_nixpkgs(self):
        lock = {
            "root": "root",
            "nodes": {
                "root": {"inputs": {"nixpkgs": "nixpkgs_2"}},
                "nixpkgs": {"locked": {"lastModified": 1 * DAY}},
                "nixpkgs_2": {"locked": {"lastModified": 1000 * DAY}},
            },
        }
        self.assertEqual(uk.lock_age_days(lock, 1020 * DAY), 20)

    def test_a_system_built_from_the_locked_darwin_rev_is_current(self):
        rev = uk.locked_darwin_rev(self.LOCK)
        self.assertTrue(uk.on_lock("/nix/store/abc-darwin-system-26.11.ff0e21a", rev))

    def test_a_system_from_another_darwin_rev_is_behind(self):
        rev = uk.locked_darwin_rev(self.LOCK)
        self.assertFalse(uk.on_lock("/nix/store/abc-darwin-system-26.11.4cff07d", rev))

    def test_an_unknown_system_is_not_called_current(self):
        rev = uk.locked_darwin_rev(self.LOCK)
        self.assertFalse(uk.on_lock("", rev))


class TestHostProbe(unittest.TestCase):
    def test_reads_a_mac_load_line(self):
        self.assertEqual(uk.load_average("12:32 up 27 days, load averages: 1.87 1.96 1.98"), 1.87)

    def test_reads_a_comma_separated_load_line(self):
        self.assertEqual(uk.load_average("09:03 up 5 days, load average: 16.16, 34.48, 50.96"), 16.16)

    def test_a_running_rebuild_marks_the_host_busy(self):
        out = "up, load averages: 1.0 1.0 1.0\n---\n/nix/store/a-darwin-system-26.11.ff0e21a\n---\n41 sudo darwin-rebuild switch\n"
        probe = uk.parse_probe(out)
        self.assertEqual(probe["builds"], ["41 sudo darwin-rebuild switch"])
        self.assertEqual(probe["system"], "/nix/store/a-darwin-system-26.11.ff0e21a")

    def test_no_builds_parses_to_an_empty_list(self):
        probe = uk.parse_probe("up, load averages: 1.0 1.0 1.0\n---\n/nix/store/a\n---\n")
        self.assertEqual(probe["builds"], [])


class TestPins(unittest.TestCase):
    def test_finds_actions_that_track_a_branch(self):
        text = "uses: actions/checkout@v7\n        uses: Foo/bar@main\n  - uses: Baz/qux@master\n"
        self.assertEqual(uk.branch_tracking_actions(text), ["Foo/bar@main", "Baz/qux@master"])

    def test_a_pin_behind_latest_needs_attention(self):
        self.assertTrue(uk.pin_is_behind({"2.2.27"}, "2.2.33"))

    def test_pin_sites_that_disagree_need_attention(self):
        self.assertTrue(uk.pin_is_behind({"2.2.33", "2.2.27"}, "2.2.33"))

    def test_a_pin_at_latest_is_fine(self):
        self.assertFalse(uk.pin_is_behind({"2.2.33"}, "2.2.33"))


class TestExit(unittest.TestCase):
    def test_could_not_tell_outranks_all_clear(self):
        self.assertEqual(uk.exit_code(attention=0, unknown=1), 2)

    def test_attention_outranks_could_not_tell(self):
        self.assertEqual(uk.exit_code(attention=1, unknown=1), 1)

    def test_all_clear(self):
        self.assertEqual(uk.exit_code(attention=0, unknown=0), 0)


if __name__ == "__main__":
    unittest.main()
