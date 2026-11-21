"""xo-toolbox.py fast-forwards a stale checkout and alerts only when it cannot.

Hosts here are clones of a bare local origin; the ssh prefix is `bash -c`.
"""

from __future__ import annotations

import contextlib
import io
import os
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path

from _loader import load

xo = load("xo-toolbox.py")

GIT_ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, env=GIT_ENV, check=True,
                          capture_output=True, text=True).stdout.strip()


def commit(repo, name, text="x"):
    (Path(repo) / name).write_text(text)
    git(repo, "add", name)
    git(repo, "commit", "-qm", name)


class Hosts(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.origin = self.tmp / "origin.git"
        git(self.tmp, "init", "-q", "--bare", "-b", "main", str(self.origin))
        seed = self.tmp / "seed"
        git(self.tmp, "clone", "-q", str(self.origin), str(seed))
        commit(seed, "a")
        git(seed, "push", "-q", "origin", "HEAD:main")
        self.seed = seed
        self.host = self.tmp / "host"
        git(self.tmp, "clone", "-q", str(self.origin), str(self.host))

    def push(self, name="b", text="x"):
        commit(self.seed, name, text)
        git(self.seed, "push", "-q", "origin", "HEAD:main")

    def run_xo(self, repo=None, prefix=("bash", "-c")):
        hosts = [("h1", list(prefix), shlex.quote(str(repo or self.host)))]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            xo.main(hosts)
        return out.getvalue()

    def behind(self):
        git(self.host, "fetch", "-q")
        return int(git(self.host, "rev-list", "--count", "HEAD..origin/main"))

    def test_behind_and_clean_fast_forwards(self):
        self.push()
        self.assertEqual(self.run_xo(), "")
        self.assertEqual(self.behind(), 0)

    def test_untouched_dirty_file_does_not_block(self):
        self.push()
        (self.host / "a").write_text("local edit")
        self.assertEqual(self.run_xo(), "")
        self.assertEqual(self.behind(), 0)
        self.assertEqual((self.host / "a").read_text(), "local edit")

    def test_touched_dirty_file_alerts_and_keeps_edit(self):
        self.push("a", "upstream edit")
        (self.host / "a").write_text("local edit")
        out = self.run_xo()
        self.assertIn("XO toolbox: h1 is 1 behind origin/main and can't fast-forward (", out)
        self.assertEqual((self.host / "a").read_text(), "local edit")

    def test_diverged_alerts(self):
        self.push()
        commit(self.host, "local")
        out = self.run_xo()
        self.assertEqual(out, "XO toolbox: h1 is 1 behind origin/main and can't fast-forward (diverged)\n")
        self.assertEqual(git(self.host, "log", "-1", "--format=%s"), "local")

    def test_wrong_branch_alerts_and_stays(self):
        git(self.host, "checkout", "-qb", "topic")
        self.push()
        out = self.run_xo()
        self.assertIn("(on branch topic)", out)
        self.assertEqual(git(self.host, "branch", "--show-current"), "topic")

    def test_up_to_date_is_silent(self):
        self.assertEqual(self.run_xo(), "")

    def test_unreachable_host_is_silent(self):
        self.assertEqual(self.run_xo(prefix=("false",)), "")

    def test_missing_checkout_is_silent(self):
        self.assertEqual(self.run_xo(repo=self.tmp / "nope"), "")

    def test_throttle_skips_within_10_min(self):
        state = self.tmp / "stamp"
        self.assertTrue(xo.due(state, now=1000.0))
        self.assertFalse(xo.due(state, now=1000.0 + 599))
        self.assertTrue(xo.due(state, now=1000.0 + 601))


if __name__ == "__main__":
    unittest.main()
