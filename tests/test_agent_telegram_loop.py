"""Loop tests for `bin/agent-telegram.py`, against a fake api.telegram.org.

The bot can spawn a three-hour run, so the properties worth proving are about
the transport, not the commands: that an unlisted chat gets nothing, that a
restart cannot replay a queued `/run`, that the offset advances so a command is
answered once, and that an unset allowlist refuses to start.

These run the real script as a subprocess -- real urllib, real env loading, real
`main()` -- because the defects being guarded against are exactly the ones a
direct function call would step over.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fake_telegram import FakeTelegram, message

SCRIPT = Path(__file__).resolve().parent.parent / "bin/agent-telegram.py"
ALLOWED, STRANGER = 4242, 9999


def run_bot(fake: FakeTelegram, *, allowlist: str | None = str(ALLOWED),
            runs: Path | None = None, polls: int = 1) -> subprocess.CompletedProcess:
    """A drain plus `polls` polls against the fake, then exit."""
    env = {
        "PATH": "/usr/bin:/bin",
        # HOME moves the run directory; TOOLBOX must stay on the real checkout,
        # because the bot loads agent-watch.py out of it.
        "TOOLBOX": str(SCRIPT.parent.parent),
        "HOME": str(runs) if runs else tempfile.gettempdir(),
        "TELEGRAM_API_BASE": fake.url,
        "TELEGRAM_BOT_TOKEN": "test:token",
        # An empty secrets file, so the test never reads the real one.
        "AGENT_NOTIFY_ENV": "/nonexistent",
    }
    if allowlist is not None:
        env["TELEGRAM_ALLOWED_CHAT_IDS"] = allowlist
    argv = [sys.executable, str(SCRIPT)]
    argv += ["--once"] if polls == 1 else ["--polls", str(polls)]
    return subprocess.run(argv, env=env, capture_output=True, text=True, timeout=60)


class TestAllowlist(unittest.TestCase):
    def test_unset_allowlist_refuses_to_start(self):
        with FakeTelegram([[], [message(1, ALLOWED, "/runs")]]) as fake:
            proc = run_bot(fake, allowlist=None)
        self.assertEqual(proc.returncode, 78)
        self.assertIn("refusing to start", proc.stderr)
        self.assertEqual(fake.sent, [], "a refusing bot must not have polled")

    def test_stranger_gets_no_reply_at_all(self):
        # Not even an error: a reply would confirm to a stranger that the bot
        # is alive and worth probing.
        with FakeTelegram([[], [message(1, STRANGER, "/runs")]]) as fake:
            proc = run_bot(fake)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(fake.sent, [])
        self.assertIn("ignored chat", proc.stderr)

    def test_allowed_chat_is_answered_once(self):
        with FakeTelegram([[], [message(1, ALLOWED, "/help")]]) as fake:
            run_bot(fake)
        self.assertEqual(len(fake.sent), 1)
        chat_id, text = fake.sent[0]
        self.assertEqual(chat_id, ALLOWED)
        self.assertIn("/status", text)

    def test_one_stranger_does_not_suppress_an_allowed_chat(self):
        batch = [message(1, STRANGER, "/run evil 480"), message(2, ALLOWED, "/help")]
        with FakeTelegram([[], batch]) as fake:
            run_bot(fake)
        self.assertEqual([c for c, _ in fake.sent], [ALLOWED])


class TestRestartSafety(unittest.TestCase):
    def test_updates_queued_before_startup_are_discarded(self):
        # Telegram holds an unacknowledged update for 24h. Without the drain a
        # bot restarted at noon would execute a /run typed at 3am.
        stale = [message(1, ALLOWED, "/run stale-run 480")]
        with FakeTelegram([stale, []]) as fake:
            proc = run_bot(fake)
        self.assertEqual(fake.sent, [], "a stale command was acted on")
        self.assertIn("discarded 1 stale update", proc.stderr)

    def test_the_drain_acknowledges_what_it_discarded(self):
        # Discarding without advancing the offset would re-fetch the same
        # update forever and never reach a live one.
        stale = [message(7, ALLOWED, "/runs")]
        with FakeTelegram([stale, []]) as fake:
            run_bot(fake)
        self.assertEqual(fake.offsets[0], None, "the drain should ask without an offset")
        self.assertEqual(fake.offsets[1], 8, "the poll should ack past update_id 7")

    def test_offset_advances_past_a_handled_update(self):
        # Two polls, because the offset a handled update sets is only visible
        # on the next request. Asserting the reply instead still passed with
        # the line that advances it deleted, so the bot would have answered
        # the same command every 50s forever -- and re-run every /stop.
        with FakeTelegram([[], [message(5, ALLOWED, "/runs")], []]) as fake:
            run_bot(fake, polls=2)
        self.assertEqual(fake.offsets, [None, None, 6],
                         "the second poll must ack past update_id 5")


    def test_a_stranger_cannot_reach_the_side_effect(self):
        # `fake.sent == []` proves no reply, not that handle() never ran. A
        # /run that spawned and was merely not acknowledged looks identical.
        with tempfile.TemporaryDirectory() as home:
            with FakeTelegram([[], [message(1, STRANGER, "/run evil 480 x")]]) as fake:
                proc = run_bot(fake, runs=Path(home))
            self.assertEqual(proc.returncode, 0)
            self.assertEqual(fake.sent, [])
            self.assertFalse((Path(home) / "Git/agent-runs/iter/evil").exists(),
                             "a stranger's /run must not create a run directory")
            self.assertFalse((Path(home) / "Git/agent-runs/logs/evil.log").exists(),
                             "a stranger's /run must not create a log")


class TestCommandsOverTheWire(unittest.TestCase):
    def test_status_of_a_missing_run_is_an_answer_not_a_crash(self):
        with tempfile.TemporaryDirectory() as home:
            with FakeTelegram([[], [message(1, ALLOWED, "/status nope")]]) as fake:
                proc = run_bot(fake, runs=Path(home))
            self.assertEqual(proc.returncode, 0)
            self.assertEqual(len(fake.sent), 1)
            self.assertIn("no such run", fake.sent[0][1])

    def test_a_failing_command_replies_instead_of_killing_the_loop(self):
        with FakeTelegram([[], [message(1, ALLOWED, "/log")]]) as fake:
            proc = run_bot(fake)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("usage: /log", fake.sent[0][1])


if __name__ == "__main__":
    unittest.main()
