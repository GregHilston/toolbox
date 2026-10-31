"""herdr-subagent.sh against a stand-in herdr that records its calls."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "dot/claude/.claude/hooks/herdr-subagent.sh"

FAKE_HERDR = """#!/bin/sh
echo "$*" >> "$HERDR_CALLS"
case "$1 $2" in
"tab create") echo '{"result":{"root_pane":{"pane_id":"w1:p9"}}}' ;;
esac
"""


class HerdrSubagent(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.calls = self.tmp / "calls"
        self.calls.touch()
        herdr = self.tmp / "herdr"
        herdr.write_text(FAKE_HERDR)
        herdr.chmod(herdr.stat().st_mode | stat.S_IEXEC)
        self.state = self.tmp / "state" / "herdr-subagent" / "s1"
        self.parent = self.tmp / "s1.jsonl"
        self.env = os.environ | {
            "HERDR_ENV": "1",
            "HERDR_BIN_PATH": str(herdr),
            "HERDR_WORKSPACE_ID": "w1",
            "HERDR_CALLS": str(self.calls),
            "HERDR_SUBAGENT_LINGER": "0",
            "XDG_STATE_HOME": str(self.tmp / "state"),
        }

    def hook(self, action: str, env: dict[str, str] | None = None) -> None:
        payload = {"session_id": "s1", "agent_id": "a1", "agent_type": "general-purpose",
                   "transcript_path": str(self.parent)}
        subprocess.run(["sh", str(HOOK), action], input=json.dumps(payload), text=True, check=True,
                       env=env or self.env)

    def write_meta(self) -> None:
        meta = self.tmp / "s1" / "subagents" / "agent-a1.meta.json"
        meta.parent.mkdir(parents=True)
        meta.write_text(json.dumps({"description": "Read HEAD", "model": "sonnet"}))

    def test_does_nothing_outside_herdr(self) -> None:
        env = {k: v for k, v in self.env.items() if k != "HERDR_ENV"}
        self.hook("start", env)
        self.assertEqual(self.calls.read_text(), "", "herdr called outside a Herdr pane")
        self.assertFalse(self.state.exists(), f"state written at {self.state}")

    def test_start_names_the_tab_and_row_by_model_and_task(self) -> None:
        self.write_meta()
        self.hook("start")
        calls = self.calls.read_text()
        self.assertIn("--label sonnet: Read HEAD --no-focus", calls)
        self.assertIn("--agent sonnet --state working --message Read HEAD", calls)
        self.assertEqual((self.state / "a1").read_text(), "w1:p9")

    def test_stop_marks_idle_closes_the_pane_and_clears_state(self) -> None:
        self.write_meta()
        self.hook("start")
        self.hook("stop")
        calls = self.calls.read_text()
        self.assertIn("--agent sonnet --state idle", calls)
        self.assertIn("pane close w1:p9", calls)
        self.assertEqual(list(self.state.iterdir()), [], "state left after stop")

    def test_a_resume_cancels_the_pending_close(self) -> None:
        self.write_meta()
        self.hook("start")
        lingering = self.env | {"HERDR_SUBAGENT_LINGER": "1"}
        payload = {"session_id": "s1", "agent_id": "a1", "transcript_path": str(self.parent)}
        stop = subprocess.Popen(["sh", str(HOOK), "stop"], stdin=subprocess.PIPE, text=True, env=lingering)
        assert stop.stdin is not None
        stop.stdin.write(json.dumps(payload))
        stop.stdin.close()
        for _ in range(50):
            if (self.state / "a1.stop").exists():
                break
            subprocess.run(["sleep", "0.05"])
        self.hook("start")
        stop.wait()
        calls = self.calls.read_text()
        self.assertNotIn("pane close", calls, f"resumed subagent's tab closed: {calls}")
        creates = calls.count("tab create")
        self.assertEqual(creates, 1, f"tabs created {creates}, want 1: {calls}")
        self.hook("stop")
        self.assertIn("pane close w1:p9", self.calls.read_text())

    def test_stop_for_an_unknown_subagent_touches_no_pane(self) -> None:
        self.hook("stop")
        self.assertEqual(self.calls.read_text(), "", "herdr called for a subagent with no tab")

    def test_session_end_closes_tabs_left_open(self) -> None:
        self.write_meta()
        self.hook("start")
        self.hook("end")
        self.assertIn("pane close w1:p9", self.calls.read_text())
        self.assertFalse(self.state.exists(), f"state left at {self.state}")


if __name__ == "__main__":
    unittest.main()
