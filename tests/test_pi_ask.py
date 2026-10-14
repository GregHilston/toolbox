"""pi-ask.py against a stand-in pi, which reads stdin to EOF first like the real one."""

from __future__ import annotations

import os
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
    import json, os, sys, time
    sys.stdin.read()  # pi does this before anything else; it hangs on an open pipe
    if os.environ.get("FAKE_PI_SLEEP"):
        time.sleep(float(os.environ["FAKE_PI_SLEEP"]))
    usage = {"input": 1000000, "cacheRead": 0, "output": 0}
    message = {"role": "assistant", "model": "cloud", "timestamp": 1792238400000, "usage": usage,
               "content": [{"type": "text", "text": "the answer, given " + sys.argv[-1]}]}
    print(json.dumps({"type": "message_end", "message": message}), flush=True)
''')


class TestPiAsk(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "bin").mkdir()
        fake = root / "bin" / "pi"
        fake.write_text(FAKE_PI)
        fake.chmod(0o755)
        self.env = dict(os.environ, HOME=self.tmp.name, PATH=f"{root / 'bin'}:{os.environ['PATH']}")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def ask(self, *args: str, **env: str) -> subprocess.CompletedProcess:
        # stdin stays an open pipe until pi-ask exits, as in the shell that hung
        # pi: pi-ask must not hand it on to pi. run() would close it at once.
        proc = subprocess.Popen([sys.executable, str(SCRIPT), *args], env=self.env | env,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True)
        try:
            proc.wait(timeout=60)
        finally:
            proc.kill()
            proc.stdin.close()
        return subprocess.CompletedProcess(proc.args, proc.returncode, proc.stdout.read(), "")

    def test_prints_the_answer_and_its_cost(self):
        out = self.ask("--session", "t1", "--dir", self.tmp.name, "hello")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("the answer, given hello", out.stdout)
        # 1M cache-miss tokens on a Saturday, off-peak Flash.
        self.assertIn("$0.1500", out.stdout)
        self.assertIn("pi-ask.py --session t1", out.stdout)

    def test_keeps_the_raw_log_across_turns(self):
        self.ask("--session", "t2", "--dir", self.tmp.name, "first")
        self.ask("--session", "t2", "--dir", self.tmp.name, "second")
        log = Path(self.tmp.name) / ".cache" / "pi-ask" / "t2.jsonl"
        self.assertEqual(log.read_text().count("message_end"), 2)

    def test_kills_a_silent_worker_and_exits_3(self):
        started = time.monotonic()
        out = self.ask("--session", "t3", "--dir", self.tmp.name, "--idle", "1", "slow", FAKE_PI_SLEEP="60")
        self.assertEqual(out.returncode, 3, out.stdout + out.stderr)
        self.assertLess(time.monotonic() - started, 30)


if __name__ == "__main__":
    unittest.main()
