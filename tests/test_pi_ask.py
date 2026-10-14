"""pi-ask.py against a stand-in pi, which reads stdin to EOF first like the real one."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "bin" / "pi-ask.py"

FAKE_PI = textwrap.dedent('''\
    #!/usr/bin/env python3
    import json, os, subprocess, sys, time
    env = os.environ.get
    sys.stdin.read()  # pi does this before anything else; it hangs on an open pipe
    assert sys.argv[-2] == "--", sys.argv
    if env("FAKE_PI_ARGV"):
        with open(env("FAKE_PI_ARGV"), "w") as f:
            json.dump({"argv": sys.argv[1:], "cwd": os.getcwd()}, f)

    def say(event):
        print(json.dumps(event), flush=True)

    def message(text, stop="stop"):
        # 1M cache-miss tokens: $0.15 at DeepSeek's off-peak Flash price, $0.30 at the gateway's.
        usage = {"input": 1000000, "cacheRead": 0, "output": 0, "cost": {"total": 0.3}}
        return {"type": "message_end", "message": {
            "role": "assistant", "model": "cloud", "timestamp": 1792238400000, "usage": usage,
            "content": [{"type": "text", "text": text}] if text else [],
            "stopReason": stop, "errorMessage": "provider said no"}}

    if env("FAKE_PI_STDERR"):
        print(env("FAKE_PI_STDERR"), file=sys.stderr, flush=True)
    for i in range(int(env("FAKE_PI_TURNS", "0"))):
        say({"type": "turn_start"})
        say(message(f"filler {i}"))
    if env("FAKE_PI_SLEEP") or env("FAKE_PI_ORPHAN"):
        sleeper = ["sh", "-c", "trap '' TERM; exec sleep 120"] if env("FAKE_PI_ORPHAN") else ["sleep", "120"]
        child = subprocess.Popen(sleeper, stdout=subprocess.DEVNULL)
        with open(env("FAKE_PI_PIDS"), "w") as f:
            f.write(f"{os.getpid()} {child.pid}")
        time.sleep(float(env("FAKE_PI_SLEEP", "0")))
    say({"type": "turn_start"})
    say(message("" if env("FAKE_PI_EMPTY") else "the answer, given " + sys.argv[-1], env("FAKE_PI_STOP", "stop")))
    if env("FAKE_PI_TAIL"):
        sys.stdout.write(env("FAKE_PI_TAIL"))
        sys.stdout.flush()
''')


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


class TestPiAsk(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "bin").mkdir()
        fake = root / "bin" / "pi"
        fake.write_text(FAKE_PI)
        fake.chmod(0o755)
        self.pids = root / "pids"
        self.env = dict(os.environ, HOME=self.tmp.name, FAKE_PI_PIDS=str(self.pids),
                        PATH=f"{root / 'bin'}:{os.environ['PATH']}")

    def tearDown(self) -> None:
        if self.pids.exists():
            for pid in map(int, self.pids.read_text().split()):
                if alive(pid):
                    os.kill(pid, signal.SIGKILL)
        self.tmp.cleanup()

    def start(self, *args: str, **env: str) -> subprocess.Popen:
        # stdin stays an open pipe, as in the shell that hung pi.
        return subprocess.Popen([sys.executable, str(SCRIPT), *args], env=self.env | env,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True)

    def ask(self, *args: str, **env: str) -> subprocess.CompletedProcess:
        proc = self.start(*args, **env)
        try:
            output = proc.stdout.read()
            proc.wait(timeout=60)
        finally:
            proc.kill()
            proc.stdin.close()
            proc.stdout.close()
        return subprocess.CompletedProcess(proc.args, proc.returncode, output, "")

    def test_prints_the_answer_and_its_cost(self):
        out = self.ask("--session", "t1", "--dir", self.tmp.name, "hello")
        self.assertEqual(out.returncode, 0, out.stdout)
        self.assertIn("the answer, given hello", out.stdout)
        # 1M cache-miss tokens on a Saturday, off-peak Flash.
        self.assertIn("$0.1500", out.stdout)
        self.assertIn("pi-ask.py --session t1", out.stdout)

    def test_a_follow_up_reports_only_its_own_turn(self):
        self.ask("--session", "t2", "--dir", self.tmp.name, "first")
        out = self.ask("--session", "t2", "--dir", self.tmp.name, "second")
        self.assertIn("given second", out.stdout)
        self.assertIn("$0.1500", out.stdout)
        log = Path(self.tmp.name) / ".cache" / "pi-ask" / "t2.jsonl"
        self.assertEqual(log.read_text().count("message_end"), 2)

    def test_passes_a_prompt_that_looks_like_an_option(self):
        out = self.ask("--session", "t3", "--dir", self.tmp.name, "---\ntitle: x\n---")
        self.assertEqual(out.returncode, 0, out.stdout)

    def test_a_failed_turn_exits_nonzero_with_its_error(self):
        out = self.ask("--session", "t4", "--dir", self.tmp.name, "hi", FAKE_PI_STOP="error")
        self.assertEqual(out.returncode, 1, out.stdout)
        self.assertIn("provider said no", out.stdout)

    def test_rejects_a_session_name_pi_would_refuse(self):
        out = self.ask("--session", "a/b", "--dir", self.tmp.name, "hi")
        self.assertEqual(out.returncode, 2, out.stdout)

    def test_rejects_a_session_name_with_a_trailing_newline(self):
        out = self.ask("--session", "t1\n", "--dir", self.tmp.name, "hi")
        self.assertEqual(out.returncode, 2, out.stdout)

    def test_a_missing_dir_is_not_reported_as_a_missing_pi(self):
        out = self.ask("--session", "t1", "--dir", "/nonexistent-pi-ask", "hi")
        self.assertEqual(out.returncode, 2, out.stdout)
        self.assertIn("not a directory", out.stdout)

    def test_a_missing_prompt_file_is_a_clear_error(self):
        out = self.ask("--session", "t1", "--dir", self.tmp.name, "@/nonexistent-pi-ask.md")
        self.assertEqual(out.returncode, 2, out.stdout)
        self.assertIn("cannot read the prompt file", out.stdout)
        self.assertNotIn("Traceback", out.stdout)

    def test_a_prompt_over_the_argument_limit_is_a_clear_error(self):
        big = Path(self.tmp.name) / "big.md"
        big.write_text("x" * 3_000_000)
        out = self.ask("--session", "t1", "--dir", self.tmp.name, f"@{big}")
        self.assertEqual(out.returncode, 1, out.stdout)
        self.assertIn("argument limit", out.stdout)
        self.assertNotIn("Traceback", out.stdout)

    def test_a_cut_off_reply_is_a_failure(self):
        out = self.ask("--session", "t1", "--dir", self.tmp.name, "hi", FAKE_PI_STOP="length")
        self.assertEqual(out.returncode, 1, out.stdout)
        self.assertIn("cut off", out.stdout)

    def test_a_failed_last_turn_does_not_pass_off_earlier_filler_as_the_answer(self):
        out = self.ask("--session", "t1", "--dir", self.tmp.name, "hi",
                       FAKE_PI_TURNS="1", FAKE_PI_EMPTY="1", FAKE_PI_STOP="error")
        self.assertEqual(out.returncode, 1, out.stdout)
        self.assertNotIn("filler 0", out.stdout)
        self.assertIn("(no answer)", out.stdout)

    def test_narrates_a_last_line_with_no_newline(self):
        out = self.ask("--session", "t1", "--dir", self.tmp.name, "hi", FAKE_PI_TAIL="pi died mid-line")
        self.assertIn("pi died mid-line", out.stdout)

    def test_starts_on_a_new_line_after_a_killed_run_left_half_of_one(self):
        log = Path(self.tmp.name) / ".cache" / "pi-ask" / "t1.jsonl"
        log.parent.mkdir(parents=True)
        log.write_bytes(b'{"type":"half')
        out = self.ask("--session", "t1", "--dir", self.tmp.name, "hi")
        self.assertEqual(out.returncode, 0, out.stdout)
        self.assertEqual(log.read_text().splitlines()[0], '{"type":"half')

    def test_kills_a_silent_worker_and_its_children_then_exits_3(self):
        started = time.monotonic()
        out = self.ask("--session", "t5", "--dir", self.tmp.name, "--idle", "1", "slow", FAKE_PI_SLEEP="60")
        self.assertEqual(out.returncode, 3, out.stdout)
        self.assertLess(time.monotonic() - started, 30)
        pi, child = map(int, self.pids.read_text().split())
        self.assertFalse(alive(pi))
        self.assertFalse(alive(child))

    def signalled(self, sig: int) -> subprocess.CompletedProcess:
        proc = self.start("--session", "t6", "--dir", self.tmp.name, "slow", FAKE_PI_SLEEP="60")
        try:
            deadline = time.monotonic() + 20
            while not self.pids.exists() and time.monotonic() < deadline:
                time.sleep(0.1)
            proc.send_signal(sig)
            output = proc.stdout.read()
            proc.wait(timeout=30)
        finally:
            proc.kill()
            proc.stdin.close()
            proc.stdout.close()
        pi, child = map(int, self.pids.read_text().split())
        time.sleep(0.5)
        self.assertFalse(alive(pi))
        self.assertFalse(alive(child))
        return subprocess.CompletedProcess(proc.args, proc.returncode, output, "")

    def test_a_terminated_pi_ask_takes_pi_with_it(self):
        out = self.signalled(signal.SIGTERM)
        self.assertEqual(out.returncode, 128 + signal.SIGTERM, out.stdout)

    def test_ctrl_c_stops_pi_and_still_prints_the_answer_block(self):
        out = self.signalled(signal.SIGINT)
        self.assertEqual(out.returncode, 128 + signal.SIGINT, out.stdout)
        self.assertNotIn("Traceback", out.stdout)
        self.assertIn("=== answer", out.stdout)
        self.assertIn("=== follow up", out.stdout)

    def test_a_hangup_stops_pi_too(self):
        out = self.signalled(signal.SIGHUP)
        self.assertEqual(out.returncode, 128 + signal.SIGHUP, out.stdout)

    def test_a_second_run_of_a_busy_session_fails_fast(self):
        first = self.start("--session", "t8", "--dir", self.tmp.name, "slow", FAKE_PI_SLEEP="60")
        try:
            deadline = time.monotonic() + 20
            while not self.pids.exists() and time.monotonic() < deadline:
                time.sleep(0.1)
            out = self.ask("--session", "t8", "--dir", self.tmp.name, "meanwhile")
            self.assertEqual(out.returncode, 5, out.stdout)
            self.assertIn("already running", out.stdout)
            self.assertNotIn("given meanwhile", out.stdout)
        finally:
            first.terminate()
            first.wait(timeout=30)
            first.stdin.close()
            first.stdout.close()

    def test_a_follow_up_without_dir_runs_where_the_first_turn_did(self):
        work = Path(self.tmp.name) / "work"
        work.mkdir()
        argv = Path(self.tmp.name) / "argv.json"
        self.ask("--session", "t9", "--dir", str(work), "first")
        out = self.ask("--session", "t9", "second", FAKE_PI_ARGV=str(argv))
        self.assertEqual(out.returncode, 0, out.stdout)
        self.assertEqual(Path(json.loads(argv.read_text())["cwd"]).resolve(), work.resolve())

    def test_a_follow_up_from_another_dir_is_refused(self):
        self.ask("--session", "t9", "--dir", self.tmp.name, "first")
        out = self.ask("--session", "t9", "--dir", "/", "second")
        self.assertEqual(out.returncode, 2, out.stdout)
        self.assertIn("runs in", out.stdout)
        self.assertNotIn("given second", out.stdout)

    def test_kills_a_child_that_ignores_sigterm_after_pi_exits(self):
        out = self.ask("--session", "t7", "--dir", self.tmp.name, "hi", FAKE_PI_ORPHAN="1")
        self.assertEqual(out.returncode, 0, out.stdout)
        _, child = map(int, self.pids.read_text().split())
        time.sleep(0.5)
        self.assertFalse(alive(child))


if __name__ == "__main__":
    unittest.main()
