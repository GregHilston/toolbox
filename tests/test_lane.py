"""lane.py against real throwaway git repos with a local bare origin.

git is real so the rebase, union merge and fast-forward checks mean something;
gh, overnight-loop.py and ./verify.sh are stand-ins that record or answer.
"""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load

lane = load("lane.py")

LOG = """\
#93 Three vehicles with their own handling and ratings
  done: plan claude/sonnet $0.19 list, work claude/sonnet $0.88 list
#94 Settings screen
  parked: plan claude/sonnet $0.10 list
#95 Title screen
"""
STOPPED = LOG + "\nStopped: queue empty. Branch overnight/2026-10-16-0628.\nDone:\n  #93 x\n"


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def write(path: Path, text: str, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    if mode:
        path.chmod(path.stat().st_mode | mode)


class LaneCase(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
               "GIT_COMMITTER_EMAIL": "t@t", "GIT_CONFIG_GLOBAL": os.devnull}
        stubs = self.root / "stubs"
        write(stubs / "gh", '#!/bin/sh\necho "$@" >> "$FAKE_GH"\n', stat.S_IXUSR)
        write(stubs / "overnight-loop.py", '#!/bin/sh\necho "$@" > "$PWD/.overnight/args"\nexec sleep 30\n',
              stat.S_IXUSR)
        self.gh_log = self.root / "gh.log"
        env.update(PATH=f"{stubs}:{os.environ['PATH']}", FAKE_GH=str(self.gh_log))
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)

        origin = self.root / "origin.git"
        git(self.root, "init", "-q", "--bare", "-b", "main", str(origin))
        seed = self.root / "seed"
        git(self.root, "clone", "-q", str(origin), str(seed))
        write(seed / "progress.md", "# progress\n")
        write(seed / "file.txt", "one\n")
        write(seed / "tests" / "baseline_count", "10\n")
        write(seed / "verify.sh", '#!/bin/sh\ncat "$VERIFY_OUT"\nexit "${VERIFY_EXIT:-0}"\n', stat.S_IXUSR)
        git(seed, "add", ".")
        git(seed, "commit", "-q", "-m", "chore: seed")
        git(seed, "push", "-q", "origin", "HEAD:main")
        self.origin = origin
        self.repo = self.root / "proj"
        git(self.root, "clone", "-q", str(origin), str(self.repo))
        self.verify_out = self.root / "verify.out"
        self.verify_out.write_text("PASS 12 tests\n")
        os.environ["VERIFY_OUT"] = str(self.verify_out)

    def make_clone(self, name: str = "b") -> Path:
        clone = self.root / f"proj-{name}"
        git(self.root, "clone", "-q", str(self.origin), str(clone))
        (clone / ".overnight").mkdir()
        return clone

    def lane_commit(self, clone: Path, branch: str, fname: str, text: str, subject: str, append: bool = True) -> None:
        if branch not in git(clone, "branch", "--format=%(refname:short)").split():
            git(clone, "checkout", "-q", "-b", branch)
        f = clone / fname
        f.write_text((f.read_text() if append else "") + text)
        git(clone, "add", fname)
        git(clone, "commit", "-q", "-m", subject)

    def main_commit(self, fname: str, text: str, append: bool = True) -> None:
        f = self.repo / fname
        f.write_text((f.read_text() if append else "") + text)
        git(self.repo, "add", fname)
        git(self.repo, "commit", "-q", "-m", "chore: main moves")


class StartTest(LaneCase):
    def test_refuses_a_running_lane(self) -> None:
        clone = self.make_clone()
        (clone / ".overnight" / "lane.pid").write_text(f"{os.getpid()}\n")
        with self.assertRaises(lane.LaneError) as cm:
            lane.start(self.repo, "b", None, [])
        self.assertIn("already running", str(cm.exception))

    def test_starts_detached_with_label_and_args(self) -> None:
        git(self.repo, "config", "wayfinder.tracker", "github")
        msg = lane.start(self.repo, "b", None, ["--harness", "claude"])
        clone = self.root / "proj-b"
        pid = int((clone / ".overnight" / "lane.pid").read_text())
        self.addCleanup(lambda: os.kill(pid, 9))
        self.assertIn(f"pid {pid}", msg)
        self.assertIn("lane.log", msg)
        self.assertEqual(git(clone, "config", "wayfinder.tracker"), "github")
        self.assertIn(".overnight/", (clone / ".git" / "info" / "exclude").read_text())
        self.assertEqual(git(clone, "status", "--porcelain"), "")
        for _ in range(50):
            if (clone / ".overnight" / "args").exists():
                break
            subprocess.run(["sleep", "0.1"])
        self.assertEqual((clone / ".overnight" / "args").read_text().strip(), "--label b --harness claude")
        with self.assertRaises(lane.LaneError):
            lane.start(self.repo, "b", None, [])


class StatusTest(LaneCase):
    def test_parses_the_log(self) -> None:
        clone = self.make_clone()
        (clone / ".overnight" / "lane.log").write_text(STOPPED)
        out = lane.status(self.repo)
        row = out.splitlines()[1]
        self.assertIn("stopped", row)
        self.assertIn("#95 Title screen", row)
        self.assertTrue(row.endswith("overnight/2026-10-16-0628"), out)
        self.assertEqual(row.split()[0], "b")

    def test_running_lane_counts(self) -> None:
        clone = self.make_clone()
        (clone / ".overnight" / "lane.log").write_text(LOG)
        (clone / ".overnight" / "lane.pid").write_text(f"{os.getpid()}\n")
        row = lane.lane_row(clone, "b")
        self.assertEqual(row, ["b", "running", "#95 Title screen", "1", "1", ""])


class FetchTest(LaneCase):
    def setUp(self) -> None:
        super().setUp()
        self.clone = self.make_clone()
        self.br = "overnight/2026-10-16-0628"

    def test_rebases_and_unions_progress(self) -> None:
        self.lane_commit(self.clone, self.br, "progress.md", "- lane note\n", "feat(x): a (#7)")
        self.main_commit("progress.md", "- main note\n")
        out = lane.fetch(self.repo, "b", None)
        wt = self.root / "proj-wt-b"
        self.assertIn(f"worktree {wt}", out)
        self.assertIn("commits 1", out)
        self.assertTrue(out.endswith("clean"), out)
        self.assertEqual(git(self.repo, "branch", "--list", "b-0628", "--format=%(refname:short)"), "b-0628")
        text = (wt / "progress.md").read_text()
        self.assertIn("- lane note", text)
        self.assertIn("- main note", text)

    def test_same_minute_branch_gets_its_own_name(self) -> None:
        self.lane_commit(self.clone, self.br, "file.txt", "x\n", "feat(x): a (#7)")
        git(self.repo, "branch", "b-0628")
        out = lane.fetch(self.repo, "b", None)
        self.assertIn("branch b-0628-2", out)

    def test_reports_conflicts(self) -> None:
        self.lane_commit(self.clone, self.br, "file.txt", "lane\n", "feat(x): a (#7)", append=False)
        self.main_commit("file.txt", "main\n", append=False)
        out = lane.fetch(self.repo, "b", None)
        self.assertIn("conflicts", out)
        self.assertIn("  file.txt", out)
        self.assertTrue((self.root / "proj-wt-b").is_dir())


class LandTest(LaneCase):
    def fetched(self, subject: str = "feat(x): a (#7)") -> Path:
        clone = self.make_clone()
        self.lane_commit(clone, "overnight/2026-10-16-0628", "file.txt", "lane\n", subject)
        self.lane_commit(clone, "overnight/2026-10-16-0628", "file.txt", "more\n", "feat(x): b (#8)")
        lane.fetch(self.repo, "b", None)
        return self.root / "proj-wt-b"

    def test_lands_raises_baseline_and_closes_issues(self) -> None:
        wt = self.fetched()
        out = lane.land(self.repo, wt, False)
        self.assertIn("PASS 12 tests", out)
        self.assertEqual((self.repo / "tests" / "baseline_count").read_text().strip(), "12")
        self.assertEqual(git(self.repo, "log", "-1", "--format=%s"), "chore: raise the test baseline to 12")
        self.assertEqual(git(self.origin, "rev-parse", "main"), git(self.repo, "rev-parse", "main"))
        calls = self.gh_log.read_text().splitlines()
        self.assertEqual(calls, ["issue close 7 --comment Merged to main; gate PASS 12.",
                                 "issue close 8 --comment Merged to main; gate PASS 12."])
        self.assertFalse(wt.exists())
        self.assertEqual(git(self.repo, "branch", "--list", "b-0628"), "")

    def test_baseline_never_lowered(self) -> None:
        wt = self.fetched()
        self.verify_out.write_text("PASS 5 tests\n")
        lane.land(self.repo, wt, False)
        self.assertEqual((self.repo / "tests" / "baseline_count").read_text().strip(), "10")

    def test_refuses_non_fast_forward(self) -> None:
        wt = self.fetched()
        self.main_commit("file.txt", "diverge\n")
        with self.assertRaises(lane.LaneError) as cm:
            lane.land(self.repo, wt, False)
        self.assertIn("not a fast-forward", str(cm.exception))
        self.assertFalse(self.gh_log.exists())

    def test_refuses_missing_pass_line(self) -> None:
        wt = self.fetched()
        self.verify_out.write_text("ERROR test_x failed\n")
        with self.assertRaises(lane.LaneError) as cm:
            lane.land(self.repo, wt, False)
        self.assertIn("PASS <n> tests", str(cm.exception))
        self.assertEqual(git(self.repo, "rev-list", "--count", "main"), "1")

    def test_failing_exit_with_pass_line_refused(self) -> None:
        wt = self.fetched()
        os.environ["VERIFY_EXIT"] = "1"
        self.addCleanup(os.environ.pop, "VERIFY_EXIT", None)
        with self.assertRaises(lane.LaneError):
            lane.land(self.repo, wt, False)

    def test_no_verify_skips_baseline(self) -> None:
        wt = self.fetched()
        self.verify_out.write_text("garbage\n")
        lane.land(self.repo, wt, True)
        self.assertEqual((self.repo / "tests" / "baseline_count").read_text().strip(), "10")
        self.assertIn("gate skipped", self.gh_log.read_text())


class StopTest(LaneCase):
    def test_touches_stop(self) -> None:
        clone = self.make_clone()
        msg = lane.stop(self.repo, "b")
        self.assertTrue((clone / ".overnight" / "STOP").exists())
        self.assertIn("STOP", msg)

    def test_unknown_lane(self) -> None:
        with self.assertRaises(lane.LaneError):
            lane.stop(self.repo, "zzz")


if __name__ == "__main__":
    unittest.main()
