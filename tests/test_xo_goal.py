"""xo-goal.py: an hourly GOAL nudge while the run log shows no goal tick."""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOAL = ROOT / "bin/xo-goal.py"
LOG = """# Run

## Goal

Speed up lp's train landing and verifying.

## Current

orders

## Journal
"""


def stamp(t: float) -> str:
    return datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M")


class XoGoal(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.log = self.tmp / "log.md"
        self.stamp = self.tmp / "goal-stamp"

    def run_goal(self) -> str:
        return subprocess.run([GOAL, self.log, self.stamp], capture_output=True, text=True, check=True).stdout

    def test_no_tick_nudges_with_the_goal_text(self) -> None:
        self.log.write_text(LOG)
        out = self.run_goal()
        self.assertIn("XO goal:", out)
        self.assertIn("Speed up lp's train landing", out)

    def test_a_recent_tick_is_quiet(self) -> None:
        self.log.write_text(LOG + f"\n### {stamp(time.time() - 600)} goal tick\n\nlandings 5\n")
        self.assertEqual(self.run_goal(), "")

    def test_an_old_tick_nudges(self) -> None:
        self.log.write_text(LOG + f"\n### {stamp(time.time() - 7200)} goal tick\n\nlandings 5\n")
        self.assertIn("XO goal:", self.run_goal())

    def test_nudges_at_most_hourly(self) -> None:
        self.log.write_text(LOG)
        self.assertIn("XO goal:", self.run_goal())
        self.assertEqual(self.run_goal(), "")
        old = time.time() - 3700
        os.utime(self.stamp, (old, old))
        self.assertIn("XO goal:", self.run_goal())

    def test_a_log_without_a_goal_is_quiet(self) -> None:
        self.log.write_text(LOG.replace("## Goal\n\nSpeed up lp's train landing and verifying.\n\n", ""))
        self.assertEqual(self.run_goal(), "")

    def test_the_loop_runs_it_with_goal(self) -> None:
        text = (ROOT / "bin/control-loop.sh").read_text()
        self.assertIn("--goal)", text)
        self.assertIn("xo-goal.py", text)


if __name__ == "__main__":
    unittest.main()
