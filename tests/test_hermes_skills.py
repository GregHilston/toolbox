"""Every command a Hermes skill tells the agent to run must exist in bin/.

A renamed script otherwise leaves the skill advertising a command that
answers "not found", and the agent falls back to web search.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "hermes" / "skills"
BIN = REPO / "bin"


def commands(skill_md: str) -> set[str]:
    """First word of each line in the skill's code blocks, if it is a script."""
    found = set()
    for block in re.findall(r"```\w*\n(.*?)```", skill_md, re.S):
        for line in block.splitlines():
            word = line.split()[0] if line.split() else ""
            if re.fullmatch(r"[\w-]+\.(py|sh)", word):
                found.add(word)
    return found


class TestSkillCommands(unittest.TestCase):
    def test_every_command_is_a_bin_script(self):
        for skill in sorted(SKILLS.glob("*/SKILL.md")):
            for name in commands(skill.read_text()):
                with self.subTest(skill=skill.parent.name, command=name):
                    self.assertTrue((BIN / name).exists(), f"{skill.parent.name} runs {name}, which is not in bin/")

    def test_the_reddit_skill_is_checked(self):
        self.assertEqual(commands((SKILLS / "reddit" / "SKILL.md").read_text()), {"reddit-search.py", "fetch-thread.py"})


if __name__ == "__main__":
    unittest.main()
