"""watch-triage.py wakes Claude for decisions and holds the routine rest."""

from __future__ import annotations

import io
import unittest

from _loader import load

wt = load("watch-triage.py")


def triage(lines: list[str], ask=lambda text: "wake") -> tuple[str, object]:
    out = io.StringIO()
    t = wt.run(lines, out, ask)
    return out.getvalue(), t


class Classify(unittest.TestCase):
    def test_each_kind(self) -> None:
        cases = {
            "lane a parked #5": "wake",
            "lane a stopped: no more issues": "wake",
            "lane a stopped: no Stopped line, it died": "wake",
            "landed: feat: x": "quiet",
            "lane a gate FAIL on #5": "quiet",
            "lane starts:": "quiet",
            "something new": "unknown",
        }
        for line, want in cases.items():
            self.assertEqual(wt.classify(line), want, line)


class Run(unittest.TestCase):
    def test_quiet_events_print_nothing(self) -> None:
        out, t = triage(["landed: a", "lane a gate FAIL on #5", "lane starts:", "  a started #1"])
        self.assertEqual(out, "")
        self.assertEqual((t.events, t.wakes), (3, 0))

    def test_a_wake_carries_the_held_quiet_events(self) -> None:
        out, t = triage(["landed: a", "lane b parked #7"])
        self.assertEqual(out, "(1 quiet: landed: a)\nlane b parked #7\n")
        self.assertEqual(t.wakes, 1)

    def test_an_unknown_line_follows_the_asker(self) -> None:
        out, _ = triage(["odd line"], ask=lambda text: "quiet")
        self.assertEqual(out, "")
        out, _ = triage(["odd line"], ask=lambda text: "wake")
        self.assertEqual(out, "odd line\n")

    def test_summary_counts(self) -> None:
        _, t = triage(["landed: a", "landed: b", "lane c parked #1"])
        self.assertEqual(t.summary(), "watch-triage: 3 events, 1 wake-ups, 2 held")


class Ask(unittest.TestCase):
    def test_a_failed_pi_ask_wakes(self) -> None:
        orig = wt.PI_ASK
        wt.PI_ASK = "/nonexistent/pi-ask"
        try:
            self.assertEqual(wt.ask_deepseek("x"), "wake")
        finally:
            wt.PI_ASK = orig


if __name__ == "__main__":
    unittest.main()
