"""Hermes skills name real scripts, and every grant names a real skill.

A renamed script leaves a skill advertising a command that answers "not
found"; a typo in a grant links nothing and says nothing. Dungeon links every
bin/ script onto the agent's PATH at start (home-lab hermes/cont-init), so
existing here is enough there too.
"""

from __future__ import annotations

import os
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "hermes" / "skills"
BIN = REPO / "bin"
HERMES_NIX = REPO / "nixos" / "modules" / "programs" / "tui" / "hermes.nix"


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
        for skill in sorted(SKILLS.glob("**/SKILL.md")):
            for name in commands(skill.read_text()):
                with self.subTest(skill=skill.parent.name, command=name):
                    script = BIN / name
                    self.assertTrue(script.exists(), f"{skill.parent.name} runs {name}, which is not in bin/")
                    self.assertTrue(os.access(script, os.X_OK), f"bin/{name} is not executable")

    def test_every_grant_names_a_skill(self):
        # The only `name = [ ... ];` lines are the botSkills entries and defaultSkills.
        lists = re.findall(r"^\s+[A-Za-z]+ = \[(.*?)\];$", HERMES_NIX.read_text(), re.M)
        grants = re.findall(r'"([\w/-]+)"', " ".join(lists))
        self.assertIn("lab-tools/reddit", grants, "the grant parser found nothing")
        for name in set(grants):
            with self.subTest(skill=name):
                self.assertTrue((SKILLS / name / "SKILL.md").exists(), f"hermes.nix grants {name}, which has no hermes/skills/{name}/SKILL.md")

    def test_the_reddit_skill_is_checked(self):
        self.assertEqual(commands((SKILLS / "lab-tools" / "reddit" / "SKILL.md").read_text()), {"reddit-search.py", "fetch-thread.py"})

    def test_new_skills_have_a_category(self):
        # Uncategorised, "reddit" is indexed as "reddit:" / "- reddit", and Gemma
        # joined those into a tool name, "reddit:reddit".
        flat = {p.parent.name for p in SKILLS.glob("*/SKILL.md")}
        self.assertEqual(flat, {"verify-agent-output", "llm-wiki-review"}, "put new skills under lab-tools/")

    def test_grants_are_at_most_one_level_deep(self):
        # prune_skills in hermes.nix looks one level down; deeper grants never revoke.
        lists = re.findall(r"^\s+[A-Za-z]+ = \[(.*?)\];$", HERMES_NIX.read_text(), re.M)
        for name in re.findall(r'"([\w/-]+)"', " ".join(lists)):
            self.assertLessEqual(name.count("/"), 1, name)


if __name__ == "__main__":
    unittest.main()
