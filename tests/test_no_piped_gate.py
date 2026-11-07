"""The no-piped-gate hook blocks a git write that rides on a piped test, and nothing else.

Runs the hook as Claude Code does: JSON on stdin, exit 2 to block.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "dot" / "claude" / ".claude" / "hooks" / "no-piped-gate.py"


def run(command: str) -> int:
    event = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": "."}
    return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(event), text=True, capture_output=True).returncode


class TestNoPipedGate(unittest.TestCase):
    def test_the_2026_11_07_commit_is_blocked(self):
        cmd = "tools/test.sh test_glossary_terms.py 2>&1 | tail -1 && tools/quick.sh && git commit -q -m x -- GLOSSARY.md"
        self.assertEqual(run(cmd), 2, "a piped test before a commit must block")

    def test_a_piped_gate_before_push_or_merge_is_blocked(self):
        self.assertEqual(run("./verify.sh | tail -1 && git push origin main"), 2, "push")
        self.assertEqual(run("tools/land_check.sh origin/main 2>&1 | tail -2 && git merge --ff-only x"), 2, "merge")
        self.assertEqual(run("uv run pytest -q | tail -1; git commit -m x"), 2, "pytest")

    def test_a_captured_exit_code_passes(self):
        cmd = "./verify.sh > out 2>&1; rc=$?; tail -1 out; [ $rc -eq 0 ] && git push"
        self.assertEqual(run(cmd), 0, "captured rc must pass")

    def test_pipefail_passes(self):
        self.assertEqual(run("set -o pipefail; ./verify.sh | tail -1 && git push"), 0, "pipefail must pass")

    def test_an_or_chain_is_not_a_pipe(self):
        self.assertEqual(run("tools/quick.sh || exit 1; git commit -m x"), 0, "|| is not a pipe")

    def test_a_pipe_after_the_write_or_without_a_test_passes(self):
        self.assertEqual(run("git commit -m x && ./verify.sh | tail -1"), 0, "pipe after the write")
        self.assertEqual(run("git log --oneline | head -3 && git push"), 0, "no test in the pipe")
        self.assertEqual(run("./verify.sh | tail -1"), 0, "no git write")

    def test_bad_input_lets_the_command_through(self):
        out = subprocess.run([sys.executable, str(HOOK)], input="not json", text=True, capture_output=True)
        self.assertEqual(out.returncode, 0, "the hook's own failure must not block")


if __name__ == "__main__":
    unittest.main()
