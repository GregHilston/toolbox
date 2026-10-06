"""Every skill follows the shared convention (skills/README.md).

One skill set serves Claude Code, pi and Hermes, so a skill that one of them
cannot load is broken for all three: Hermes drops a skill with invalid YAML
without a word, and a renamed script leaves a skill advertising a command that
answers "not found".
"""

from __future__ import annotations

import os
import re
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SHARED = REPO / "skills"
HERMES_ONLY = REPO / "hermes" / "skills"
BIN = REPO / "bin"

# agentskills.io plus Claude extensions pi tolerates.
ALLOWED_KEYS = {
    "name", "description", "license", "compatibility", "metadata", "allowed-tools",
    "disable-model-invocation", "argument-hint", "model", "disallowed-tools",
}


def tracked_skills() -> list[Path]:
    """SKILL.md files in git: synced/ and mozilla-* are gitignored."""
    out = subprocess.run(["git", "ls-files", "*/SKILL.md"], cwd=REPO, capture_output=True, text=True, check=True)
    return [REPO / p for p in out.stdout.split() if p.startswith(("skills/", "hermes/skills/"))]


def frontmatter(skill_md: str) -> dict[str, str]:
    """Top-level keys and their text; a `|` block becomes its joined lines."""
    front = skill_md.split("---")[1]
    fields: dict[str, str] = {}
    key = None
    for line in front.splitlines():
        if m := re.match(r"^([A-Za-z0-9_-]+):\s?(.*)$", line):
            key, fields[key] = m.group(1), m.group(2)
        elif key and line.startswith(" "):
            fields[key] = (fields[key].lstrip("|>-+").strip() + " " + line.strip()).strip()
    return fields


def commands(skill_md: str) -> set[str]:
    """First word of each line in the skill's code blocks, if it is a script."""
    found = set()
    for block in re.findall(r"```\w*\n(.*?)```", skill_md, re.S):
        for line in block.splitlines():
            word = line.split()[0] if line.split() else ""
            if re.fullmatch(r"[\w-]+\.(py|sh)", word):
                found.add(word)
    return found


class TestSkills(unittest.TestCase):
    def test_the_skill_list_is_not_empty(self):
        self.assertIn(SHARED / "reddit" / "SKILL.md", tracked_skills())

    def test_frontmatter_follows_the_spec(self):
        for skill in tracked_skills():
            with self.subTest(skill=skill.parent.name):
                fields = frontmatter(skill.read_text())
                self.assertEqual(fields.get("name"), skill.parent.name, "name must match the directory")
                self.assertRegex(fields["name"], r"^[a-z0-9]+(-[a-z0-9]+)*$")
                self.assertTrue(0 < len(fields.get("description", "")) <= 1024)
                self.assertLessEqual(set(fields), ALLOWED_KEYS, "a field no harness reads")

    def test_frontmatter_values_have_no_bare_colon(self):
        # YAML reads "key: a: b" as a nested mapping and fails, and Hermes then
        # drops the whole skill without a word. The wikipedia skill did this.
        for skill in tracked_skills():
            for line in skill.read_text().split("---")[1].splitlines():
                key, _, value = line.partition(": ")
                with self.subTest(skill=skill.parent.name, key=key.strip()):
                    if value and not line.startswith(" ") and not value.startswith(("'", '"', "[", "{", "|", ">")):
                        self.assertFalse(": " in value or value.endswith(":"), "quote this value, or reword it without a colon")

    def test_skills_are_one_level_deep(self):
        # Claude Code loads only ~/.claude/skills/<name>/SKILL.md.
        for skill in tracked_skills():
            with self.subTest(skill=str(skill.relative_to(REPO))):
                self.assertEqual(skill.parent.parent, SHARED if skill.is_relative_to(SHARED) else HERMES_ONLY)

    def test_every_command_is_a_bin_script(self):
        for skill in tracked_skills():
            for name in commands(skill.read_text()):
                with self.subTest(skill=skill.parent.name, command=name):
                    script = BIN / name
                    self.assertTrue(script.exists(), f"{skill.parent.name} runs {name}, which is not in bin/")
                    self.assertTrue(os.access(script, os.X_OK), f"bin/{name} is not executable")

    def test_the_reddit_skill_is_checked(self):
        self.assertEqual(commands((SHARED / "reddit" / "SKILL.md").read_text()), {"reddit-search.py", "fetch-thread.py"})


if __name__ == "__main__":
    unittest.main()
