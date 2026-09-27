"""The no-ai-attribution hook blocks attributed commits and PRs, and nothing else.

Runs the hook as Claude Code does: JSON on stdin, exit 2 to block.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "dot" / "claude" / ".claude" / "hooks" / "no-ai-attribution.py"
TRAILER = "Co-Authored-" + "By: Claude Opus <noreply@anthropic.com>"
FOOTER = "Generated with [" + "Claude Code](https://claude.com/claude-code)"


def run(command: str, cwd: str = ".") -> int:
    event = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd}
    return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(event), text=True, capture_output=True).returncode


class TestNoAiAttribution(unittest.TestCase):
    def test_a_trailer_in_a_commit_message_is_blocked(self):
        self.assertEqual(run(f'git commit -m "fix: x\n\n{TRAILER}"'), 2)

    def test_a_heredoc_commit_is_blocked(self):
        self.assertEqual(run(f"git commit -F - <<'EOF'\nfix: x\n\n{TRAILER}\nEOF"), 2)

    def test_a_pr_body_file_is_read(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "body.md").write_text(f"## Why\n\n{FOOTER}\n")
            self.assertEqual(run("gh pr create --title t --body-file body.md", cwd=d), 2)
            self.assertEqual(run("gh pr edit 7 --body-file=body.md", cwd=d), 2)

    def test_clean_writes_pass(self):
        self.assertEqual(run('git commit -m "fix: x"'), 0)
        with tempfile.TemporaryDirectory() as d:
            Path(d, "body.md").write_text("## Why\n\nBecause.\n")
            self.assertEqual(run("gh pr create --title t --body-file body.md", cwd=d), 0)

    def test_reading_the_words_is_not_writing_them(self):
        self.assertEqual(run(f'git log --grep="{TRAILER}"'), 0)
        self.assertEqual(run(f"grep -r '{TRAILER}' ."), 0)

    def test_prose_about_the_lines_is_not_the_lines(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "body.md").write_text('Blocks a `Co-Authored-By: Claude` trailer or a "Generated with Claude Code" line.\n')
            self.assertEqual(run("gh pr create --title t --body-file body.md", cwd=d), 0)

    def test_bad_input_never_blocks(self):
        result = subprocess.run([sys.executable, str(HOOK)], input="not json", text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
