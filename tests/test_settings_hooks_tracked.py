"""Every script settings.json runs from this repo is tracked in git.

The global gitignore ignores `.claude/`, so a new hook stays untracked unless
added with `git add -f`; it then works on the machine that wrote it and fails
everywhere else, CI included.
"""

from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = ROOT / "dot/claude/.claude/settings.json"
# ~/.claude/hooks links into this repo.
PREFIXES = {"~/.claude/hooks/": "dot/claude/.claude/hooks/", "~/Git/toolbox/": ""}


def commands(node) -> list[str]:
    if isinstance(node, dict):
        return [c for k, v in node.items() for c in ([v] if k == "command" and isinstance(v, str) else commands(v))]
    if isinstance(node, list):
        return [c for v in node for c in commands(v)]
    return []


class SettingsHooksTracked(unittest.TestCase):
    def test_every_repo_script_is_tracked(self) -> None:
        tracked = set(subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split())
        paths = []
        for cmd in commands(json.loads(SETTINGS.read_text())):
            for prefix, repo in PREFIXES.items():
                if m := re.match(re.escape(prefix) + r"(\S+)", cmd):
                    paths.append(repo + m[1])
        self.assertGreater(len(paths), 5, "found too few hooks; did the settings layout change?")
        self.assertEqual([p for p in paths if p not in tracked], [], "git add -f these")


if __name__ == "__main__":
    unittest.main()
