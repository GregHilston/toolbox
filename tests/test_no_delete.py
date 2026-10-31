"""The no-delete hook blocks an agent's deleting commands, and only those.

Runs the hook as Claude Code does: JSON on stdin, exit 2 to block.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "dot" / "claude" / ".claude" / "hooks" / "no-delete.py"

BLOCKED = [
    "rm -rf /dev/null",
    "rm x",
    "/bin/rm -Rf x",
    "rmdir d",
    "unlink f",
    "cd /tmp && rm -rf x",
    "bash a.sh; rm -rf /dev/null; mkdir -p d",
    "ls; rm -r x",
    "ls\nrm -rf x",
    "ls | xargs rm",
    "xargs -n 1 rm -rf",
    "FOO=1 rm x",
    "sudo rm x",
    "env rm x",
    "command rm x",
    "timeout 5 rm x",
    "nohup rm x &",
    "bash -c 'rm -rf x'",
    'bash -lc "rm -rf x"',
    "sh -xc 'rm -rf x'",
    'bash -c -- "rm -rf x"',
    "eval rm x",
    'echo "rm -rf x" | sh',
    "printf 'rm -rf x' | sh -s",
    "echo $(rm x)",
    "echo `rm x`",
    'echo "$(rm x)"',
    "(rm x)",
    "find . -delete",
    "find . -name a -exec rm {} +",
    "ssh dungeon 'rm -rf x'",
    "ssh -o ConnectTimeout=5 dungeon rm x",
    "git clean -fdx",
    "git -C /repo clean -f",
    "git worktree remove x",
    "git worktree prune",
    "git branch -D x",
    "git -C /r branch -d x",
    "git stash drop",
    "git reflog expire --all",
    "rsync -a --delete a b",
    "dd if=/dev/zero of=x",
    "shred x",
    "tools/worktree_gc.sh --remove",
    "worktree_gc.sh",
    "rm 'unbalanced",
]

ALLOWED = [
    "ls -la",
    'grep "rm -rf" install.sh',
    "rg 'rm -rf' .",
    "echo 'a; rm -rf /'",
    'git commit -m "docs: never rm a file"',
    "git commit -F - <<'E'\nfix: x\n\nrm x was wrong\nE",
    "cat > notes.md <<'EOF'\nrm -rf everything\nEOF\nls",
    "git status; git log -1",
    "git branch -a",
    "git worktree list",
    "git stash list",
    "firm x",
    "./rmx",
    "uv run pytest tests/test_rm.py",
    "find . -name '*.py'",
    "find . -exec grep rm {} +",
    "ssh dungeon 'docker ps'",
    "timeout 5 ls",
    "git log --format='%h it''s'",
    "curl 'https://x/#rm'; ls",
    "unbalanced 'quote",
]


def run(command: str) -> int:
    event = {"tool_name": "Bash", "tool_input": {"command": command}}
    return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(event), text=True, capture_output=True).returncode


class TestNoDelete(unittest.TestCase):
    def test_deleting_commands_are_blocked(self):
        for command in BLOCKED:
            with self.subTest(command=command):
                self.assertEqual(run(command), 2)

    def test_everything_else_passes(self):
        for command in ALLOWED:
            with self.subTest(command=command):
                self.assertEqual(run(command), 0)

    def test_bad_input_passes(self):
        result = subprocess.run([sys.executable, str(HOOK)], input="not json", text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
