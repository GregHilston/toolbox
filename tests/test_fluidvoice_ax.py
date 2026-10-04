"""fluidvoice-ax builds with the stock toolchain and refuses to run without apps.

Activation compiles it with /usr/bin/swiftc on each Mac, so a source that no longer
builds would surface only as a warning mid-deploy. The no-argument case exits before
the Accessibility prompt, so this never pops a system dialog.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parent.parent / "nixos" / "modules" / "darwin" / "fluidvoice-ax.swift"


def toolchain() -> bool:
    if shutil.which("swiftc") is None:
        return False
    return subprocess.run(["xcode-select", "-p"], capture_output=True).returncode == 0


@unittest.skipUnless(toolchain(), "needs swiftc from the Command Line Tools")
class TestFluidVoiceAx(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.binary = Path(cls.tmp.name, "fluidvoice-ax")
        build = subprocess.run(["swiftc", "-O", str(SOURCE), "-o", str(cls.binary)], capture_output=True, text=True)
        cls.build_error = build.stderr if build.returncode else None

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_builds(self):
        self.assertIsNone(self.build_error)

    def test_no_apps_is_a_usage_error(self):
        if self.build_error:
            self.skipTest("did not build")
        run = subprocess.run([str(self.binary)], capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 2)
        self.assertIn("usage: fluidvoice-ax", run.stderr)


if __name__ == "__main__":
    unittest.main()
