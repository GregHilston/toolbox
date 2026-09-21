"""Tests for `bin/agent-telegram.py`.

The bot can spawn a three-hour run on the box, so what is tested is mostly the
refusals: who is allowed to talk to it, what an argument is allowed to be, and
whether a malformed command can reach `subprocess` or a path outside the run
directory. The happy paths are thin wrappers over `agent-watch.py`, which has
its own suite.

`handle()` is pure apart from the filesystem, so the tests point the module's
module-level paths at a tmpdir rather than mocking.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from _loader import load

tg = load("agent-telegram.py")


class Paths(unittest.TestCase):
    """Repoint the module's globals at a tmpdir for the duration of a test."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.runs, self.logs = root / "iter", root / "logs"
        self.runs.mkdir()
        self.logs.mkdir()
        self._saved = (tg.RUNS, tg.LOGS)
        tg.RUNS, tg.LOGS = self.runs, self.logs

    def tearDown(self) -> None:
        tg.RUNS, tg.LOGS = self._saved
        self.tmp.cleanup()


class TestArgumentValidation(Paths):
    def test_run_name_must_be_a_run_name(self):
        for bad in ("../etc", "Long-B", "a b", "x" * 40, "-lead", ""):
            with self.subTest(bad=bad):
                out = tg.start_run(bad, 30, "note")
                self.assertIn("bad run name", out, f"{bad!r} was accepted")

    def test_budget_is_bounded(self):
        for bad in (0, -5, 481, 100000):
            with self.subTest(bad=bad):
                self.assertIn("bad budget", tg.start_run("ok-name", bad, ""))

    def test_refuses_to_reuse_an_existing_run_directory(self):
        (self.runs / "taken").mkdir()
        self.assertIn("already exists", tg.start_run("taken", 30, ""))

    def test_tail_log_cannot_escape_the_log_directory(self):
        # `LOGS / f"{name}.log"` with a traversing name would read any .log on
        # the box; only the name check stands between the two.
        self.assertIn("bad run name", tg.tail_log("../../../../var/log/system"))

    def test_status_rejects_a_traversing_name(self):
        self.assertIn("bad run name", tg.render_run("../../.ssh"))


class TestDispatch(Paths):
    def test_unknown_command_does_not_dispatch(self):
        out = tg.handle("/deploy production")
        self.assertIn("unknown command", out)
        self.assertIn("/status", out)  # falls back to help

    def test_bare_text_is_not_a_command(self):
        self.assertIn("unknown command", tg.handle("what is happening"))

    def test_telegram_start_is_help_not_a_run(self):
        # Telegram sends /start on first contact; it must not mean "start a run".
        self.assertIn("/run <name>", tg.handle("/start"))

    def test_run_requires_a_numeric_budget(self):
        self.assertIn("usage: /run", tg.handle("/run long-c soon"))
        self.assertIn("usage: /run", tg.handle("/run long-c"))

    def test_group_suffix_is_stripped(self):
        # In a group chat Telegram delivers "/runs@mybot".
        self.assertEqual(tg.handle("/runs@hermes_bot"), tg.handle("/runs"))

    def test_log_tail_is_capped(self):
        (self.logs / "long-b.log").write_text("\n".join(str(i) for i in range(500)))
        self.assertEqual(len(tg.handle("/log long-b 999").splitlines()), 100)

    def test_log_reports_a_missing_log_rather_than_raising(self):
        self.assertIn("no orchestrator log", tg.handle("/log never-ran"))


class TestRunListing(Paths):
    def test_empty_directory_is_not_an_error(self):
        self.assertEqual(tg.list_runs(), "no runs yet")

    def test_run_without_a_board_is_listed_as_unknown(self):
        (self.runs / "half-built").mkdir()
        self.assertIn("card=?", tg.list_runs())


class TestEnvLoading(unittest.TestCase):
    def test_reads_the_secrets_file_when_the_shell_did_not(self):
        with tempfile.TemporaryDirectory() as d:
            env = Path(d) / ".env"
            env.write_text(
                '# comment\n\nTELEGRAM_BOT_TOKEN=123:abc\n'
                'TELEGRAM_CHAT_ID="456"\nMALFORMED\n'
            )
            saved_file, saved_env = tg.ENV_FILE, dict(os.environ)
            for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
                os.environ.pop(key, None)
            tg.ENV_FILE = env
            try:
                tg.load_env()
                self.assertEqual(os.environ["TELEGRAM_BOT_TOKEN"], "123:abc")
                self.assertEqual(os.environ["TELEGRAM_CHAT_ID"], "456")  # quotes stripped
            finally:
                tg.ENV_FILE = saved_file
                os.environ.clear()
                os.environ.update(saved_env)

    def test_an_already_set_token_wins_over_the_file(self):
        saved_file, saved = tg.ENV_FILE, os.environ.get("TELEGRAM_BOT_TOKEN")
        os.environ["TELEGRAM_BOT_TOKEN"] = "from-shell"
        tg.ENV_FILE = Path("/nonexistent")
        try:
            tg.load_env()
            self.assertEqual(os.environ["TELEGRAM_BOT_TOKEN"], "from-shell")
        finally:
            tg.ENV_FILE = saved_file
            if saved is None:
                os.environ.pop("TELEGRAM_BOT_TOKEN", None)
            else:
                os.environ["TELEGRAM_BOT_TOKEN"] = saved


if __name__ == "__main__":
    unittest.main()
