"""notes-task.py lands one tagged checkbox in quick-todo.md and pushes it.

The end-to-end tests run the script against a clone of a bare origin, as it
would run from a terminal, and read the result back from a second clone.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load

task = load("notes-task.py")

SCRIPT = Path(__file__).resolve().parent.parent / "bin" / "notes-task.py"
NOTE = """---
tags: [productivity]
---

## Todo: must do.

- [ ] feed tim #todo

## Watch: waiting on someone else.

_Nothing here._

- [x] old #watch ✅ 2026-08-21

## Later: someday

- [ ] buy scanner #later
"""


class TaskLineTest(unittest.TestCase):
    def test_adds_the_tag_and_due_date(self):
        self.assertEqual(task.task_line("todo", "call  the\tplumber", "2026-10-20"),
                         "- [ ] call the plumber #todo 📅 2026-10-20")

    def test_rejects_empty_text(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            task.task_line("todo", "   ", None)

    def test_rejects_a_text_already_tagged(self):
        for text in ("ping Dausen #watch", "someday #Later", "x #todo/home"):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "tag"):
                task.task_line("todo", text, None)

    def test_keeps_other_tags(self):
        self.assertEqual(task.task_line("later", "fix light #house", None), "- [ ] fix light #house #later")

    def test_rejects_a_bad_date(self):
        for due in ("2026-13-01", "20261020", "2026-1-5", "tomorrow"):
            with self.subTest(due=due), self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
                task.task_line("todo", "x", due)


class InsertTest(unittest.TestCase):
    def test_appends_to_the_end_of_its_section(self):
        out = task.insert(NOTE, "todo", "- [ ] new #todo")
        self.assertIn("- [ ] feed tim #todo\n- [ ] new #todo\n\n## Watch", out)

    def test_watch_lands_after_its_last_item(self):
        out = task.insert(NOTE, "watch", "- [ ] new #watch")
        self.assertIn("✅ 2026-08-21\n- [ ] new #watch\n\n## Later", out)

    def test_last_section_ends_the_file(self):
        self.assertTrue(task.insert(NOTE, "later", "- [ ] new #later").endswith("#later\n- [ ] new #later\n"))

    def test_no_section_appends_at_the_end(self):
        self.assertEqual(task.insert("# Tasks\n\n- [ ] a\n\n", "watch", "- [ ] b #watch"),
                         "# Tasks\n\n- [ ] a\n- [ ] b #watch\n\n")


class EndToEndTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        gitconfig = self.tmp / "gitconfig"
        gitconfig.write_text("[init]\n\tdefaultBranch = main\n[commit]\n\tgpgsign = false\n"
                             "[user]\n\tname = Test\n\temail = test@example.com\n")
        self.origin = self.tmp / "origin.git"
        self.vault = self.tmp / "vault"
        self.env = {**os.environ, "GIT_CONFIG_GLOBAL": str(gitconfig), "GIT_CONFIG_NOSYSTEM": "1",
                    "NOTES_DIR": str(self.vault), "NOTES_SYNC": str(self.tmp / "absent.sh")}
        self.git(self.tmp, "init", "-q", "--bare", str(self.origin))
        self.git(self.tmp, "clone", "-q", str(self.origin), str(self.vault))
        (self.vault / "quick-todo.md").write_text(NOTE)
        self.git(self.vault, "add", "quick-todo.md")
        self.git(self.vault, "commit", "-qm", "seed")
        self.git(self.vault, "push", "-q", "origin", "main")

    def git(self, cwd: Path, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=cwd, env=self.env, capture_output=True, text=True,
                              check=True).stdout.strip()

    def run_task(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT), *args], env=self.env, capture_output=True, text=True)

    def test_pushes_only_the_note(self):
        (self.vault / "scratch.md").write_text("unrelated\n")
        proc = self.run_task("todo", "call", "the plumber", "--due", "2026-10-20")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("added to quick-todo.md: - [ ] call the plumber #todo 📅 2026-10-20", proc.stdout)
        self.assertIn("pushed", proc.stdout)
        self.assertEqual(self.git(self.vault, "show", "--name-only", "--format=", "origin/main"), "quick-todo.md")
        self.assertIn("call the plumber", self.git(self.vault, "show", "origin/main:quick-todo.md"))
        self.assertTrue((self.vault / "scratch.md").exists())

    def test_rebases_onto_a_change_from_the_phone(self):
        phone = self.tmp / "phone"
        self.git(self.tmp, "clone", "-q", str(self.origin), str(phone))
        (phone / "other.md").write_text("from the phone\n")
        self.git(phone, "add", "other.md")
        self.git(phone, "commit", "-qm", "phone")
        self.git(phone, "push", "-q")
        proc = self.run_task("later", "fix the front light")
        self.assertIn("pushed", proc.stdout)
        self.git(phone, "pull", "-q")
        self.assertIn("- [ ] fix the front light #later", (phone / "quick-todo.md").read_text())

    def test_a_failed_push_keeps_the_commit(self):
        self.git(self.vault, "remote", "set-url", "origin", str(self.tmp / "gone.git"))
        proc = self.run_task("watch", "reply from Dausen")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("not pushed", proc.stdout)
        self.assertIn("#watch", self.git(self.vault, "log", "-1", "--format=%s"))

    def test_hermes_sync_script_does_the_git_work(self):
        hook = self.tmp / "notes-sync.sh"
        hook.write_text('#!/bin/sh\necho "$NOTES_VAULT|$1|$2" > "$NOTES_VAULT/../called"\n')
        hook.chmod(0o755)
        proc = self.run_task("todo", "plug in detectors")
        self.assertIn("pushed", proc.stdout)  # sanity: the default path still works
        self.env["NOTES_SYNC"] = str(hook)
        proc = self.run_task("todo", "feed the cat")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual((self.tmp / "called").read_text().strip(),
                         f"{self.vault}|push|docs(tasks): add #todo feed the cat")

    def test_rejects_bad_input_without_writing(self):
        proc = self.run_task("todo", "ping #watch")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("notes-task:", proc.stderr)
        self.assertEqual((self.vault / "quick-todo.md").read_text(), NOTE)

    def test_a_missing_note_fails(self):
        (self.vault / "quick-todo.md").unlink()
        proc = self.run_task("todo", "x")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("cannot write", proc.stderr)


if __name__ == "__main__":
    unittest.main()
