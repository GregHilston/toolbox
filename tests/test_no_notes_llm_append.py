"""The no-notes-llm-append hook blocks `>>` onto a missing file under notes/llm, and nothing else.

Runs the hook as Claude Code does: JSON on stdin, exit 2 to block.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "dot" / "claude" / ".claude" / "hooks" / "no-notes-llm-append.py"
NOTES = os.path.expanduser("~/Git/notes")
MISSING = "commander-log-9999-01-01-tmp-does-not-exist"


def run(command: str, cwd: str = NOTES) -> int:
    event = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd}
    return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(event), text=True, capture_output=True).returncode


class TestNoNotesLlmAppend(unittest.TestCase):
    def test_relative_append_to_a_missing_file_is_blocked(self):
        self.assertEqual(run(f"cat >> llm/{MISSING}"), 2)
        self.assertEqual(run(f">>llm/{MISSING}"), 2)
        self.assertEqual(run(f"echo hi >> './llm/{MISSING}'"), 2)

    def test_absolute_and_home_paths_are_blocked(self):
        self.assertEqual(run(f"cat >> {NOTES}/llm/{MISSING}", cwd="/"), 2)
        self.assertEqual(run(f"cat >> ~/Git/notes/llm/{MISSING}", cwd="/"), 2)
        self.assertEqual(run(f"cat >> {MISSING}", cwd=f"{NOTES}/llm"), 2)

    def test_a_leading_cd_moves_the_base(self):
        self.assertEqual(run(f"cd {NOTES} && cat >> llm/{MISSING}", cwd="/tmp"), 2)
        self.assertEqual(run(f"cd /tmp && cat >> llm/{MISSING}", cwd=NOTES), 0)

    def test_append_to_an_existing_file_passes(self):
        existing = next(Path(NOTES, "llm").glob("*.md"), None)
        if existing is None:
            self.skipTest("no llm note to append to")
        self.assertEqual(run(f"cat >> llm/{existing.name}"), 0)

    def test_paths_outside_notes_llm_pass(self):
        self.assertEqual(run(f"cat >> {NOTES}/{MISSING}"), 0)
        self.assertEqual(run(f"cat >> /tmp/{MISSING}", cwd="/"), 0)
        self.assertEqual(run(f"cat >> llm/{MISSING}", cwd="/tmp"), 0)

    def test_single_redirect_and_unresolvable_targets_pass(self):
        self.assertEqual(run(f"echo hi > llm/{MISSING}"), 0)
        self.assertEqual(run(f"echo hi >> llm/$NAME"), 0)
        self.assertEqual(run("echo hi 2>&1"), 0)

    def test_bad_input_lets_the_command_through(self):
        out = subprocess.run([sys.executable, str(HOOK)], input="not json", text=True, capture_output=True)
        self.assertEqual(out.returncode, 0)


if __name__ == "__main__":
    unittest.main()
