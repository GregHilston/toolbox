"""The fleet switch: a file that makes every pi starter refuse DeepSeek."""

from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load

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

    def test_pi_rpc_exits_76(self):
        self.on()
        rpc = load("pi-rpc.py")
        with contextlib.redirect_stderr(io.StringIO()) as err:
            code = rpc.main(["run", "--dir", self.dir.name, "--prompt", "hi"])
        self.assertEqual(code, 76)
        self.assertIn("NO DEEPSEEK", err.getvalue())


if __name__ == "__main__":
    unittest.main()
