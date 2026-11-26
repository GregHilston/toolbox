"""The no-repo-moves hook blocks subagent git moves in Greg's working copies only."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "dot" / "claude" / ".claude" / "hooks" / "no-repo-moves-in-subagents.py"
spec = importlib.util.spec_from_file_location("_no_repo_moves", HOOK)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

G = Path.home() / "Git"
ELSEWHERE = Path("/tmp")

# (command, cwd)
BLOCKED = [
    (f"git -C {G}/loser-picks checkout origin/main", ELSEWHERE),
    ("git -C ~/Git/loser-picks checkout origin/main", ELSEWHERE),
    (f"cd {G}/gridkeep && git checkout origin/main", ELSEWHERE),
    ("cd ~/Git/dradis && git reset --hard", ELSEWHERE),
    ("git checkout origin/main", G / "loser-picks"),
    ("git switch -", G / "auto-factory" / "src"),
    ("git stash", G / "dradis"),
    ("git pull", G / "gridkeep"),
    ("git restore .", G / "gridkeep"),
    ("git clean -fd", G / "gridkeep"),
    ("git rebase origin/main", G / "gridkeep"),
    ("git cherry-pick abc", G / "gridkeep"),
    ("git revert abc", G / "gridkeep"),
    ("git merge x", G / "gridkeep"),
    ("git fetch && git checkout x", G / "gridkeep"),
    ("git -c core.x=1 checkout x", G / "gridkeep"),
    ("bash -c 'git checkout x'", G / "gridkeep"),
]

ALLOWED = [
    ("git show origin/main:README.md", G / "loser-picks"),
    ("git grep foo origin/main", G / "loser-picks"),
    (f"git -C {G}/loser-picks fetch", ELSEWHERE),
    ("git log --oneline", G / "dradis"),
    ("git diff origin/main", G / "dradis"),
    ("git status", G / "dradis"),
    ("git stash list", G / "dradis"),
    ("git checkout x", G / "loser-picks-worktrees" / "feat"),
    (f"git -C {G}/loser-picks-worktrees/feat checkout x", ELSEWHERE),
    (f"cd {G}/gridkeep-worktrees/a && git reset --hard", G / "gridkeep"),
    ("git checkout x", Path.home() / ".auto-factory" / "runs" / "r1"),
    ("git checkout x", ELSEWHERE),
    ("git checkout x", G / "toolbox"),
    ("echo git checkout x", G / "gridkeep"),
]


class Refusal(unittest.TestCase):
    def test_blocked(self) -> None:
        for command, cwd in BLOCKED:
            with self.subTest(command=command, cwd=cwd):
                self.assertIsNotNone(hook.refusal(command, cwd))

    def test_allowed(self) -> None:
        for command, cwd in ALLOWED:
            with self.subTest(command=command, cwd=cwd):
                self.assertIsNone(hook.refusal(command, cwd))


class Payload(unittest.TestCase):
    def run_hook(self, **extra) -> int:
        event = {"tool_input": {"command": "git checkout origin/main"}, "cwd": str(G / "loser-picks"), **extra}
        return subprocess.run([str(HOOK)], input=json.dumps(event), text=True, capture_output=True).returncode

    def test_subagent_blocked(self) -> None:
        self.assertEqual(self.run_hook(agent_id="a1"), 2)

    def test_main_session_allowed(self) -> None:
        self.assertEqual(self.run_hook(), 0)


if __name__ == "__main__":
    unittest.main()
