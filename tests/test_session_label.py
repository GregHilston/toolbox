"""session-label: derives project/role and hands them to hc label."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "bin" / "session-label"


class SessionLabel(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        fake = self.tmp / "hc"
        fake.write_text('#!/bin/sh\necho "$@" > "$HC_LOG"\n')
        fake.chmod(0o755)
        self.log = self.tmp / "log"
        self.env = os.environ | {"PATH": f"{self.tmp}:{os.environ['PATH']}", "HC_LOG": str(self.log)}
        self.repo = self.tmp / "gridkeep"
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)

    def run_it(self, *args):
        return subprocess.run([str(SCRIPT), *args], capture_output=True, text=True, env=self.env)

    def test_cag_takes_the_repo_name(self):
        self.assertEqual(self.run_it("t17", "cag", str(self.repo)).returncode, 0)
        self.assertEqual(self.log.read_text().strip(), "label t17 project=gridkeep role=cag")

    def test_commander_is_fleet(self):
        self.assertEqual(self.run_it("t3", "commander", str(self.repo)).returncode, 0)
        self.assertEqual(self.log.read_text().strip(), "label t3 project=fleet role=commander")

    def test_bad_role_refused(self):
        out = self.run_it("t3", "boss", str(self.repo))
        self.assertEqual(out.returncode, 2)
        self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()
