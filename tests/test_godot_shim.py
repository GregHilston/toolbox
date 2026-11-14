"""shims/godot: a default time limit on headless runs, and nothing else changes."""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

SHIM = Path(__file__).resolve().parent.parent / "shims" / "godot"
FAKE = """#!/bin/sh
all="$*"
[ "$1" = --headless ] && shift
case "$1" in
  --sleep) sleep "$2" & wait ;;
  --exit) exit "$2" ;;
  *) echo "args: $all" ;;
esac
"""


class TestGodotShim(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        real = Path(self.tmp.name) / "bin" / "godot"
        real.parent.mkdir()
        real.write_text(FAKE)
        real.chmod(0o755)
        self.real = real
        # shim dir first, as .zshenv puts it; the shim must skip itself.
        self.env = {"PATH": f"{SHIM.parent}:{real.parent}:/usr/bin:/bin", "HOME": self.tmp.name}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_godot(self, *args: str, **env: str):
        start = time.monotonic()
        out = subprocess.run(["godot", *args], env={**self.env, **env}, capture_output=True, text=True, timeout=30)
        return out, time.monotonic() - start

    def test_headless_run_over_the_limit_is_killed_with_124(self):
        out, took = self.run_godot("--headless", "--sleep", "20", GODOT_TIMEOUT="1")
        self.assertEqual(out.returncode, 124)
        self.assertIn("1s", out.stderr)
        self.assertLess(took, 10)

    def test_the_kill_takes_the_whole_process_group(self):
        marker = Path(self.tmp.name) / "pid"
        script = Path(self.tmp.name) / "bin" / "godot"
        script.write_text(f'#!/bin/sh\nsleep 30 &\necho $! > {marker}\nwait\n')
        out, _ = self.run_godot("--headless", GODOT_TIMEOUT="1")
        self.assertEqual(out.returncode, 124)
        time.sleep(0.5)
        with self.assertRaises(ProcessLookupError):
            os.kill(int(marker.read_text()), 0)

    def test_headless_run_that_finishes_passes_its_exit_code_through(self):
        out, _ = self.run_godot("--headless", "--exit", "3")
        self.assertEqual(out.returncode, 3)
        out, _ = self.run_godot("--headless", "--path", "x")
        self.assertEqual((out.returncode, out.stdout.strip()), (0, "args: --headless --path x"))

    def test_zero_disables_the_limit(self):
        out, _ = self.run_godot("--headless", "--sleep", "2", GODOT_TIMEOUT="0")
        self.assertEqual(out.returncode, 0)

    def test_without_headless_it_execs_straight_through(self):
        out, took = self.run_godot("--sleep", "2", GODOT_TIMEOUT="1")
        self.assertEqual(out.returncode, 0)
        self.assertGreater(took, 1.9)

    def test_a_symlink_to_the_shim_is_skipped_not_recursed_into(self):
        farm = Path(self.tmp.name) / "farm"
        farm.mkdir()
        (farm / "godot").symlink_to(SHIM)
        out, _ = self.run_godot("--headless", "x", PATH=f"{farm}:{self.real.parent}:/usr/bin:/bin")
        self.assertEqual(out.stdout.strip(), "args: --headless x")


if __name__ == "__main__":
    unittest.main()
