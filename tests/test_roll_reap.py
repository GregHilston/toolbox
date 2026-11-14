"""roll_reap: orphaned gate processes die, anything near a running agent lives."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROLL = ROOT / "bin" / "orchestrator-roll"


class TestReap(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.cwd = base / "claude-501" / "scratchpad"
        self.cwd.mkdir(parents=True)
        self.projects = base / "projects"
        self.projects.mkdir()
        self.env = dict(os.environ, ROLL_REAP_NAMES="sleep", ROLL_REAP_GRACE="1",
                        ROLL_AGENT_QUIET="60", CLAUDE_PROJECTS_DIR=str(self.projects))  # fmt: skip
        # Orphaned to init, as a process left by a finished agent is.
        subprocess.run(["sh", "-c", f"cd {self.cwd} && (sleep 47 </dev/null >/dev/null 2>&1 &)"], check=True)
        self.addCleanup(subprocess.run, ["pkill", "-f", "^sleep 47$"])
        time.sleep(2.5)  # past the 1 s grace

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def alive(self) -> bool:
        return subprocess.run(["pgrep", "-f", "^sleep 47$"], capture_output=True).returncode == 0

    def reap(self, *flags: str) -> str:
        return subprocess.run([sys.executable, str(ROLL), "--reap", *flags], env=self.env,
                              capture_output=True, text=True, timeout=30).stdout  # fmt: skip

    def test_dry_run_names_the_process_and_kills_nothing(self):
        out = self.reap("--dry-run")
        self.assertIn("would kill: sleep 47", out)
        self.assertIn(str(self.cwd.resolve()), out)
        self.assertTrue(self.alive())

    def test_reap_kills_it_and_says_so(self):
        out = self.reap()
        self.assertIn("killed: sleep 47", out)
        time.sleep(0.5)
        self.assertFalse(self.alive())

    def test_a_recently_written_subagent_transcript_protects_everything(self):
        sub = self.projects / "proj" / "session" / "subagents"
        sub.mkdir(parents=True)
        (sub / "agent-abc.jsonl").write_text("{}")
        out = self.reap()
        self.assertIn("reaping nothing", out)
        self.assertTrue(self.alive())

    def test_a_process_outside_a_scratchpad_or_worktree_is_left_alone(self):
        self.env["ROLL_REAP_NAMES"] = "sleep"
        subprocess.run(["pkill", "-f", "^sleep 47$"])
        subprocess.run(["sh", "-c", "cd / && (sleep 47 </dev/null >/dev/null 2>&1 &)"], check=True)
        time.sleep(2.5)
        out = self.reap()
        self.assertNotIn("killed", out)
        self.assertTrue(self.alive())

    def test_age_parsing(self):
        sys.path.insert(0, str(ROOT / "bin"))
        import roll_reap

        self.assertEqual(roll_reap.seconds("05:07"), 307)
        self.assertEqual(roll_reap.seconds("1:02:03"), 3723)
        self.assertEqual(roll_reap.seconds("2-00:00:10"), 172810)


if __name__ == "__main__":
    unittest.main()
