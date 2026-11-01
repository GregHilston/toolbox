"""orch-next.py starts one openable successor per repo, from a handoff that holds its first message."""

from __future__ import annotations

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

    def test_the_command_is_a_named_remote_background_session(self) -> None:
        cmd = nxt.command(self.handoff, "go", "orch-x")
        self.assertEqual(cmd[:4], ["claude", "--bg", "--remote-control", "orch-x"])
        self.assertNotIn("-p", cmd)
        self.assertIn(str(self.handoff), cmd[-1])
        self.assertTrue(cmd[-1].endswith("go"))
        self.assertIn("lane.py status", cmd[-1])

    def test_a_slash_command_stays_first_in_the_prompt(self) -> None:
        cmd = orch.command(Path("h.md"), "/swarm Resume.", "orch-x")
        self.assertTrue(cmd[-1].startswith("/swarm Resume."), f"prompt starts {cmd[-1][:40]!r}")
        self.assertIn("h.md", cmd[-1], "the prompt names the handoff")

    def test_dry_run_starts_nothing(self) -> None:
        with mock.patch.object(nxt.subprocess, "run") as run:
            self.assertIn("would run", nxt.start(self.handoff, self.dir, dry_run=True))
        run.assert_not_called()

    def _launch(self, out: str = "backgrounded \u00b7 abc123\n") -> mock.MagicMock:
        return mock.MagicMock(returncode=0, stdout=out, stderr="")

    def test_start_reports_id_url_and_how_to_stop(self) -> None:
        with (
            mock.patch.object(nxt.subprocess, "run", return_value=self._launch()) as run,
            mock.patch.object(nxt, "session_url", return_value="https://claude.ai/code/session_X"),
        ):
            msg = nxt.start(self.handoff, self.dir)
        self.assertEqual(run.call_args.kwargs["cwd"], self.dir)
        for want in ("abc123", "https://claude.ai/code/session_X", "claude attach abc123", "claude stop abc123"):
            self.assertIn(want, msg)
        self.assertEqual((self.dir / "state" / f"{self.dir.name}.id").read_text().strip(), "abc123")

    def test_a_live_earlier_orchestrator_blocks_a_second_start_and_is_named(self) -> None:
        (self.dir / "state").mkdir()
        (self.dir / "state" / f"{self.dir.name}.id").write_text("abc123\n")
        with (
            mock.patch.object(nxt, "live_ids", return_value={"abc123"}),
            mock.patch.object(nxt.subprocess, "run") as run,
        ):
            with self.assertRaises(nxt.HandoffError) as cm:
                nxt.start(self.handoff, self.dir)
        self.assertIn("abc123", str(cm.exception))
        self.assertIn("claude stop abc123", str(cm.exception))
        run.assert_not_called()

    def test_a_stopped_earlier_orchestrator_does_not_block(self) -> None:
        (self.dir / "state").mkdir()
        (self.dir / "state" / f"{self.dir.name}.id").write_text("old111\n")
        with (
            mock.patch.object(nxt, "live_ids", return_value=set()),
            mock.patch.object(nxt.subprocess, "run", return_value=self._launch()),
            mock.patch.object(nxt, "session_url", return_value=None),
        ):
            self.assertIn("URL not up yet", nxt.start(self.handoff, self.dir))

    def test_a_failed_launch_is_an_error(self) -> None:
        bad = mock.MagicMock(returncode=1, stdout="", stderr="Workspace not trusted")
        with mock.patch.object(nxt.subprocess, "run", return_value=bad):
            with self.assertRaises(nxt.HandoffError):
                nxt.start(self.handoff, self.dir)

    def test_the_url_is_found_in_noisy_terminal_output(self) -> None:
        noisy = mock.MagicMock(stdout="\x1b[2Jis active \u00b7 at https://claude.ai/code/session_011yAbC9\x1b[39m")
        with mock.patch.object(nxt.subprocess, "run", return_value=noisy):
            self.assertEqual(nxt.session_url("abc123", wait=0), "https://claude.ai/code/session_011yAbC9")


if __name__ == "__main__":
    unittest.main()
