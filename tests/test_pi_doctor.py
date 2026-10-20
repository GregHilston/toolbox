"""pi-doctor flags unlinked config, missing tools and stale repos; no network."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load

pd = load("pi-doctor.py")


def git(repo: Path, *a: str) -> None:
    subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)


class TestLinks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.repo, self.agent = root / "toolbox", root / "agent"
        self.src = self.repo / "dot" / "pi" / ".pi" / "agent"
        (self.src / "prompts").mkdir(parents=True)
        (self.src / "extensions").mkdir()
        for f in ("AGENTS.md", "pi-fff.json", "extensions/gateway-fallback.ts"):
            (self.src / f).write_text("x")
        self.agent.mkdir()
        (self.agent / "extensions").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def link_all(self):
        for f in pd.LINKED:
            (self.agent / f).unlink(missing_ok=True)
            (self.agent / f).symlink_to(self.src / f)

    def test_linked_is_clean(self):
        self.link_all()
        self.assertEqual(pd.check_links(self.agent, self.repo), [])

    def test_missing_is_reported(self):
        self.link_all()
        (self.agent / "AGENTS.md").unlink()
        self.assertEqual(len(pd.check_links(self.agent, self.repo)), 1)

    def test_real_copy_is_not_linked(self):
        self.link_all()
        (self.agent / "pi-fff.json").unlink()
        (self.agent / "pi-fff.json").write_text("copy")
        self.assertIn("not linked", pd.check_links(self.agent, self.repo)[0])


class TestRepo(unittest.TestCase):
    def test_behind_origin_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            origin, clone = Path(d) / "o", Path(d) / "c"
            origin.mkdir()
            git(origin, "init", "-q", "-b", "main")
            git(origin, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "a")
            subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True)
            self.assertEqual(pd.check_repo(clone), [])
            git(origin, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "b")
            self.assertIn("1 commits behind", pd.check_repo(clone)[0])

    def test_missing_repo(self):
        self.assertIn("missing", pd.check_repo(Path("/nonexistent/repo"))[0])


class TestTools(unittest.TestCase):
    def test_missing_tool(self):
        with mock.patch.object(pd.shutil, "which", side_effect=lambda n: None if n == "netcheck" else "/x"):
            self.assertEqual(pd.check_tools(["lab-alerts", "netcheck"]), ["netcheck not on PATH"])


if __name__ == "__main__":
    unittest.main()
