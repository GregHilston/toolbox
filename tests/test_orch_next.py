"""orch-next.py starts a successor only from a handoff that holds its first message."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load

nxt = load("orch-next.py")

HANDOFF = "# Handoff\n\n```\nold\n```\n\nPaste this:\n\n```\n/swarm resume lanes a, b\n```\n"


class OrchNext(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.handoff = self.dir / "h.md"
        self.handoff.write_text(HANDOFF)
        patch = mock.patch.object(nxt, "STATE", self.dir / "state")
        patch.start()
        self.addCleanup(patch.stop)

    def test_first_message_is_the_last_fenced_block(self) -> None:
        self.assertEqual(nxt.first_message(self.handoff), "/swarm resume lanes a, b")

    def test_a_handoff_without_a_block_is_refused(self) -> None:
        self.handoff.write_text("# Handoff\nno message here\n")
        with self.assertRaises(nxt.HandoffError):
            nxt.start(self.handoff, self.dir)

    def test_a_missing_handoff_is_refused(self) -> None:
        with self.assertRaises(nxt.HandoffError):
            nxt.start(self.dir / "nope.md", self.dir)

    def test_the_prompt_names_the_handoff_and_carries_the_message(self) -> None:
        cmd = nxt.command(self.handoff, "go")
        self.assertEqual(cmd[:2], ["claude", "-p"])
        self.assertIn(str(self.handoff), cmd[2])
        self.assertTrue(cmd[2].endswith("go"))
        self.assertIn("lane.py status", cmd[2])

    def test_dry_run_starts_nothing(self) -> None:
        with mock.patch.object(nxt.subprocess, "Popen") as popen:
            self.assertIn("would run", nxt.start(self.handoff, self.dir, dry_run=True))
        popen.assert_not_called()

    def test_start_launches_detached_and_records_the_pid(self) -> None:
        with mock.patch.object(nxt.subprocess, "Popen") as popen:
            popen.return_value.pid = os.getpid()
            self.assertIn("started pid", nxt.start(self.handoff, self.dir))
        self.assertTrue(popen.call_args.kwargs["start_new_session"])
        self.assertEqual(popen.call_args.kwargs["cwd"], self.dir)

    def test_a_live_earlier_successor_blocks_a_second_start(self) -> None:
        (self.dir / "state").mkdir()
        (self.dir / "state" / "pid").write_text(f"{os.getpid()}\n")
        with mock.patch.object(nxt.subprocess, "Popen") as popen:
            with self.assertRaises(nxt.HandoffError):
                nxt.start(self.handoff, self.dir)
        popen.assert_not_called()

    def test_a_dead_pid_does_not_block(self) -> None:
        (self.dir / "state").mkdir()
        (self.dir / "state" / "pid").write_text("999999999\n")
        with mock.patch.object(nxt.subprocess, "Popen") as popen:
            popen.return_value.pid = 4242
            nxt.start(self.handoff, self.dir)
        popen.assert_called_once()


if __name__ == "__main__":
    unittest.main()
