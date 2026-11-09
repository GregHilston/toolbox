"""worktree-done deletes work, so these pin when it must refuse and keep everything.

Each test builds a real repository with a bare origin and runs the script as
a subprocess: the safety rests on git's own refusals, which a mock cannot show.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin"
TOOL = BIN / "worktree-done"
HOOK = BIN / "worktree-done-hook"


def git(cwd, *args):
    out = subprocess.run(
        ["git", "-C", str(cwd), "-c", "user.email=t@t", "-c", "user.name=t", *args],
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0, f"git {args} failed: {out.stderr}"
    return out.stdout.strip()


class Repo(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.origin = self.root / "origin.git"
        self.main = self.root / "main"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.origin)], check=True)
        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.main)], check=True, capture_output=True)
        (self.main / "a.txt").write_text("a\n")
        (self.main / ".gitignore").write_text("*.log\n")
        git(self.main, "add", "-A")
        git(self.main, "commit", "-qm", "init")
        git(self.main, "push", "-q", "origin", "main")

    def worktree(self, name, commit=True, land=True):
        path = self.root / "wt" / name
        git(self.main, "worktree", "add", "-q", str(path), "-b", f"worktree/{name}")
        if commit:
            (path / f"{name}.txt").write_text(name)
            git(path, "add", "-A")
            git(path, "commit", "-qm", f"work {name}")
            if land:
                git(self.main, "merge", "-q", "--ff-only", f"worktree/{name}")
                git(self.main, "push", "-q", "origin", "main")
        return path

    def run_tool(self, *args, cwd=None, env=None):
        full = {**os.environ, **(env or {})}
        return subprocess.run(
            [str(TOOL), *args], cwd=cwd or self.main, capture_output=True, text=True, env=full
        )

    def branches(self):
        return git(self.main, "branch", "--format=%(refname:short)").split()


class TestRemoval(Repo):
    def test_removes_landed_clean_worktree_and_branch(self):
        wt = self.worktree("a")
        out = self.run_tool()
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), f"REMOVED {wt} (worktree/a)")
        self.assertFalse(wt.exists(), "worktree directory still there")
        self.assertNotIn("worktree/a", self.branches())

    def test_keeps_unlanded_commit_silently(self):
        wt = self.worktree("a", land=False)
        out = self.run_tool()
        self.assertEqual(out.stdout, "", "a non-candidate prints nothing")
        self.assertTrue(wt.exists())
        self.assertIn("worktree/a", self.branches())

    def test_verbose_names_the_skip(self):
        self.worktree("a", land=False)
        out = self.run_tool("--verbose")
        self.assertIn("SKIP", out.stdout)

    def test_skips_fresh_worktree_with_no_own_commits(self):
        wt = self.worktree("fresh", commit=False)
        out = self.run_tool()
        self.assertEqual(out.stdout, "")
        self.assertTrue(wt.exists())

    def test_keeps_worktree_with_untracked_file(self):
        wt = self.worktree("a")
        (wt / "scratch.txt").write_text("keep me")
        out = self.run_tool()
        self.assertEqual(out.returncode, 0)
        self.assertRegex(out.stdout, rf"^KEPT {re.escape(str(wt))}: .*scratch\.txt")
        self.assertEqual((wt / "scratch.txt").read_text(), "keep me")
        self.assertIn("worktree/a", self.branches())

    def test_keeps_worktree_with_modified_tracked_file(self):
        wt = self.worktree("a")
        (wt / "a.txt").write_text("changed\n")
        out = self.run_tool()
        self.assertRegex(out.stdout, rf"^KEPT {re.escape(str(wt))}: .*a\.txt")
        self.assertEqual((wt / "a.txt").read_text(), "changed\n")

    def test_kept_line_lists_at_most_five_paths(self):
        wt = self.worktree("a")
        for i in range(8):
            (wt / f"f{i}.txt").write_text("x")
        out = self.run_tool()
        self.assertEqual(len(re.findall(r"f\d\.txt", out.stdout)), 5, out.stdout)

    def test_ignored_files_do_not_block(self):
        wt = self.worktree("a")
        (wt / "build.log").write_text("noise")
        out = self.run_tool()
        self.assertEqual(out.stdout.strip(), f"REMOVED {wt} (worktree/a)")
        self.assertFalse(wt.exists())

    def test_usage_says_ignored_files_go_with_the_worktree(self):
        out = self.run_tool("--help")
        self.assertIn(".gitignore", out.stdout)

    def test_never_touches_main_checkout(self):
        git(self.main, "checkout", "-q", "-b", "other")
        (self.main / "o.txt").write_text("o")
        git(self.main, "add", "-A")
        git(self.main, "commit", "-qm", "o")
        git(self.main, "push", "-q", "origin", "other:main")
        out = self.run_tool("--repo", str(self.main), cwd=self.root)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout, "")
        self.assertTrue(self.main.exists())

    def test_skips_the_worktree_holding_the_cwd(self):
        wt = self.worktree("a")
        sub = wt / "deep"
        sub.mkdir()
        out = self.run_tool("--repo", str(self.main), cwd=sub)
        self.assertEqual(out.stdout, "")
        self.assertTrue(wt.exists())

    def test_skips_detached_head(self):
        wt = self.worktree("a")
        git(wt, "checkout", "-q", "--detach")
        out = self.run_tool()
        self.assertEqual(out.stdout, "")
        self.assertTrue(wt.exists())

    def test_explicit_path_limits_the_run(self):
        a = self.worktree("a")
        b = self.worktree("b")
        out = self.run_tool(str(a))
        self.assertEqual(out.stdout.strip(), f"REMOVED {a} (worktree/a)")
        self.assertTrue(b.exists())

    def test_repo_flag_from_outside(self):
        wt = self.worktree("a")
        out = self.run_tool("--repo", str(self.main), cwd=self.root)
        self.assertIn("REMOVED", out.stdout)
        self.assertFalse(wt.exists())

    def test_not_a_repo_is_an_error(self):
        out = self.run_tool("--repo", str(self.root))
        self.assertEqual(out.returncode, 1)


class TestNoRemoval(Repo):
    def test_dry_run_touches_nothing(self):
        wt = self.worktree("a")
        out = self.run_tool("--dry-run")
        self.assertEqual(out.returncode, 0)
        self.assertIn(f"{wt} (worktree/a)", out.stdout)
        self.assertNotIn("REMOVED", out.stdout)
        self.assertTrue(wt.exists())
        self.assertIn("worktree/a", self.branches())

    def test_check_lists_only_refusals(self):
        clean = self.worktree("clean")
        dirty = self.worktree("dirty")
        (dirty / "scratch.txt").write_text("x")
        out = self.run_tool("--check")
        self.assertEqual(out.returncode, 0)
        lines = out.stdout.strip().splitlines()
        self.assertEqual(len(lines), 1, out.stdout)
        self.assertTrue(lines[0].startswith(f"KEPT {dirty}:"), lines[0])
        self.assertTrue(clean.exists() and dirty.exists())

    def test_fetch_failure_removes_nothing(self):
        wt = self.worktree("a")
        git(self.main, "remote", "set-url", "origin", str(self.root / "nowhere.git"))
        out = self.run_tool()
        self.assertEqual(out.returncode, 1)
        self.assertTrue(wt.exists())
        self.assertIn("worktree/a", self.branches())


    def test_no_fetch_skips_the_fetch_and_trusts_the_local_ref(self):
        wt = self.worktree("a")
        git(self.main, "remote", "set-url", "origin", str(self.root / "nowhere.git"))
        out = self.run_tool("--no-fetch", "--check")
        self.assertEqual(out.returncode, 0, f"exit {out.returncode}, want 0: {out.stderr}")
        self.assertTrue(wt.exists(), "--check must leave the worktree")

class TestSource(unittest.TestCase):
    FORBIDDEN = [
        r"\brm\b",
        r"\brmdir\b",
        r"--force\b",
        r"(?<![\w-])-f\b",
        r"(?<![\w-])-D\b",
        r"git clean",
        r"rmtree",
        r"os\.remove",
        r"unlink",
        r"--delete",
        r"-delete\b",
    ]

    def test_no_deleting_command_in_either_script(self):
        for path in (TOOL, HOOK):
            src = path.read_text()
            for pat in self.FORBIDDEN:
                self.assertIsNone(re.search(pat, src), f"{path.name} matches {pat!r}")


def hook(mode, event, env=None):
    return subprocess.run(
        [str(HOOK), mode],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )


class TestHook(Repo):
    def stub(self, text):
        path = self.root / "stub.sh"
        path.write_text(f"#!/bin/sh\necho \"$@\" >> '{self.root}/calls'\n{text}\n")
        path.chmod(0o755)
        return {"WORKTREE_DONE_BIN": str(path)}

    def calls(self):
        f = self.root / "calls"
        return f.read_text() if f.exists() else ""

    def push_event(self, command, cwd=None):
        return {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "cwd": str(cwd or self.main),
            "tool_input": {"command": command},
            "tool_response": {"stdout": "", "interrupted": False},
        }

    def test_ignores_non_push(self):
        env = self.stub("echo REMOVED x")
        out = hook("post-push", self.push_event("git status"), env)
        self.assertEqual(out.stdout, "")
        self.assertEqual(self.calls(), "")

    def test_ignores_quoted_git_push(self):
        env = self.stub("echo REMOVED x")
        for cmd in ('echo "git push"', "echo 'then git push later'", "git commit -m 'git push fix'"):
            out = hook("post-push", self.push_event(cmd), env)
            self.assertEqual(out.stdout, "", cmd)
        self.assertEqual(self.calls(), "")

    def test_runs_on_git_push_and_emits_context(self):
        env = self.stub("echo 'REMOVED /x (b)'")
        out = hook("post-push", self.push_event("git push origin main"), env)
        self.assertEqual(out.returncode, 0)
        data = json.loads(out.stdout)["hookSpecificOutput"]
        self.assertEqual(data["hookEventName"], "PostToolUse")
        self.assertIn("REMOVED /x (b)", data["additionalContext"])
        self.assertIn(f"--repo {self.main}", self.calls())

    def test_finds_push_in_a_chain_and_after_wrappers(self):
        env = self.stub("echo hi")
        for cmd in ("GRIDKEEP_NO_DEPLOY=1 git push", "make && git push -q", "rtk git push", "git -C . push"):
            (self.root / "calls").unlink(missing_ok=True)
            hook("post-push", self.push_event(cmd), env)
            self.assertIn("--repo", self.calls(), cmd)

    def test_silent_when_tool_prints_nothing(self):
        env = self.stub("true")
        out = hook("post-push", self.push_event("git push"), env)
        self.assertEqual(out.stdout, "")

    def test_skips_interrupted_push(self):
        env = self.stub("echo hi")
        ev = self.push_event("git push")
        ev["tool_response"]["interrupted"] = True
        self.assertEqual(hook("post-push", ev, env).stdout, "")
        self.assertEqual(self.calls(), "")

    def test_silent_outside_a_repo(self):
        env = self.stub("echo hi")
        out = hook("post-push", self.push_event("git push", cwd=self.root), env)
        self.assertEqual((out.returncode, out.stdout), (0, ""))
        self.assertEqual(self.calls(), "")

    def test_real_push_removes_landed_worktree(self):
        wt = self.worktree("a")
        out = hook("post-push", self.push_event("git push"))
        self.assertIn("REMOVED", out.stdout)
        self.assertFalse(wt.exists())

    def test_stop_emits_system_message_only_for_kept(self):
        env = self.stub("echo 'KEPT /w: git would refuse'")
        out = hook("stop", {"hook_event_name": "Stop", "cwd": str(self.main)}, env)
        self.assertEqual(out.returncode, 0)
        msg = json.loads(out.stdout)["systemMessage"]
        self.assertIn("KEPT /w", msg)
        self.assertIn("--check", self.calls())

        env = self.stub("echo 'REMOVED /w (b)'")
        out = hook("stop", {"hook_event_name": "Stop", "cwd": str(self.main)}, env)
        self.assertEqual(out.stdout, "")

    def test_stop_silent_outside_a_repo(self):
        env = self.stub("echo 'KEPT /w: x'")
        out = hook("stop", {"hook_event_name": "Stop", "cwd": str(self.root)}, env)
        self.assertEqual((out.returncode, out.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
