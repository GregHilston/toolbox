"""The fleet switch: a file that makes every pi starter refuse DeepSeek, and an XO alert on spend."""

from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load

BIN = Path(__file__).resolve().parent.parent / "bin"


class Switch(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.file = Path(self.dir.name) / "no-deepseek"
        patch = mock.patch.dict(os.environ, {"NO_DEEPSEEK_FILE": str(self.file)})
        patch.start()
        self.addCleanup(patch.stop)

    def on(self, reason="claude only until 04:00"):
        self.file.write_text(reason + "\n")


class Refusal(Switch):
    def test_helper_follows_the_file(self):
        pf = load("deepseek-preflight.py")
        self.assertIsNone(pf.no_deepseek_refusal("cloud"))
        self.on()
        text = pf.no_deepseek_refusal("cloud")
        self.assertIn(str(self.file), text)
        self.assertIn("claude only until 04:00", text)
        self.assertIsNone(pf.no_deepseek_refusal("litellm/local-small"))

    def test_pi_ask_exits_76_before_starting_pi(self):
        self.on()
        pi_ask = load("pi-ask.py")
        with mock.patch.object(sys, "argv", ["pi-ask.py", "--session", "t-nods", "x"]), \
                mock.patch.object(pi_ask.subprocess, "Popen") as popen, \
                contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(pi_ask.main(), 76)
        popen.assert_not_called()
        self.assertIn("claude only until 04:00", err.getvalue())

    def test_overnight_loop_exits_76_for_a_pi_worker(self):
        self.on()
        with tempfile.TemporaryDirectory() as cwd:
            r = subprocess.run([sys.executable, str(BIN / "overnight-loop.py"), "--harness", "pi", "--allow-peak"],
                               cwd=cwd, capture_output=True, text=True, env=os.environ | {"HOME": cwd})
        self.assertEqual(r.returncode, 76, r.stderr)
        self.assertIn("NO DEEPSEEK", r.stderr)

    def test_pi_rpc_exits_76(self):
        self.on()
        rpc = load("pi-rpc.py")
        with contextlib.redirect_stderr(io.StringIO()) as err:
            code = rpc.main(["run", "--dir", self.dir.name, "--prompt", "hi"])
        self.assertEqual(code, 76)
        self.assertIn("NO DEEPSEEK", err.getvalue())


class XoAlert(Switch):
    ROWS = [{"metric": {"user_agent": "pi/1", "client_ip": "10.0.0.5"}, "value": [0, "900.4"]},
            {"metric": {"user_agent": "curl", "client_ip": "10.0.0.9"}, "value": [0, "3"]}]

    def run_main(self, fetch):
        xo = load("xo-deepseek.py")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            xo.main(fetch)
        return out.getvalue()

    def test_alerts_with_top_caller(self):
        self.on()
        self.assertEqual(
            self.run_main(lambda q: self.ROWS),
            "XO deepseek: 903 requests in 15 min under no-deepseek (claude only until 04:00); "
            "top caller user_agent=pi/1 client_ip=10.0.0.5 (900)\n")

    def test_quiet_without_the_file(self):
        self.assertEqual(self.run_main(lambda q: self.ROWS), "")

    def test_quiet_when_requests_did_not_rise(self):
        self.on()
        self.assertEqual(self.run_main(lambda q: []), "")
        self.assertEqual(self.run_main(lambda q: [{"metric": {}, "value": [0, "0.2"]}]), "")

    def test_quiet_when_prometheus_fails(self):
        self.on()
        def boom(q):
            raise OSError("down")
        self.assertEqual(self.run_main(boom), "")


if __name__ == "__main__":
    unittest.main()
