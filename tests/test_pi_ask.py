"""pi-ask.py against a stand-in pi, which reads stdin to EOF first like the real one."""

from __future__ import annotations

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
    sys.stdin.read()  # pi does this before anything else; it hangs on an open pipe
    assert sys.argv[-2] == "--", sys.argv
    if os.environ.get("FAKE_PI_SLEEP"):
        child = subprocess.Popen(["sleep", "120"])
        with open(os.environ["FAKE_PI_PIDS"], "w") as f:
            f.write(f"{os.getpid()} {child.pid}")
        time.sleep(float(os.environ["FAKE_PI_SLEEP"]))
    usage = {"input": 1000000, "cacheRead": 0, "output": 0}
    message = {"role": "assistant", "model": "cloud", "timestamp": 1792238400000, "usage": usage,
               "content": [{"type": "text", "text": "the answer, given " + sys.argv[-1]}],
               "stopReason": os.environ.get("FAKE_PI_STOP", "stop"), "errorMessage": "provider said no"}
    print(json.dumps({"type": "message_end", "message": message}), flush=True)
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

    def test_kills_a_silent_worker_and_its_children_then_exits_3(self):
        started = time.monotonic()
        out = self.ask("--session", "t5", "--dir", self.tmp.name, "--idle", "1", "slow", FAKE_PI_SLEEP="60")
        self.assertEqual(out.returncode, 3, out.stdout)
        self.assertLess(time.monotonic() - started, 30)
        pi, child = map(int, self.pids.read_text().split())
        self.assertFalse(alive(pi))
        self.assertFalse(alive(child))

    def test_a_terminated_pi_ask_takes_pi_with_it(self):
        proc = self.start("--session", "t6", "--dir", self.tmp.name, "slow", FAKE_PI_SLEEP="60")
        try:
            deadline = time.monotonic() + 20
            while not self.pids.exists() and time.monotonic() < deadline:
                time.sleep(0.1)
            proc.terminate()
            proc.wait(timeout=30)
        finally:
            proc.kill()
            proc.stdin.close()
            proc.stdout.close()
        pi, child = map(int, self.pids.read_text().split())
        time.sleep(0.5)
        self.assertFalse(alive(pi))
        self.assertFalse(alive(child))


if __name__ == "__main__":
    unittest.main()
