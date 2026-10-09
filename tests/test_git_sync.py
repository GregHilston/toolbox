"""git-sync lands commits under the far host's identity, or changes nothing.

Each test builds a bare origin, a "far" clone (the host that pushes) and a
"near" clone (citadel), and swaps ssh for a local shell via RELAY_SSH. The
script runs end to end, as it would from a terminal.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from _loader import load

relay_mod = load("git-sync.py")

SCRIPT = Path(__file__).resolve().parent.parent / "bin" / "git-sync.py"
FAKE_SSH = shlex.join([sys.executable, "-c", "import subprocess, sys; sys.exit(subprocess.call(['sh', '-c', sys.argv[2]]))"])
WORK = ("Work Account", "work@example.com")
HOME_ID = ("Home Account", "home@example.com")


class GitRelayTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.home = self.tmp / "home"
        gitconfig = self.tmp / "gitconfig"
        gitconfig.write_text("[init]\n\tdefaultBranch = main\n[commit]\n\tgpgsign = false\n")
        self.env = {
            **os.environ,
            "HOME": str(self.home),
            "GIT_CONFIG_GLOBAL": str(gitconfig),
            "GIT_CONFIG_NOSYSTEM": "1",
            "RELAY_SSH": FAKE_SSH,
        }
        self.origin = self.tmp / "origin.git"
        self.run_git(self.tmp, "init", "-q", "--bare", str(self.origin))
        seed = self.clone(self.tmp / "seed", HOME_ID)
        self.commit(seed, "a.txt", "one\n", "seed")
        self.run_git(seed, "push", "-q", "origin", "main")
        self.far = self.clone(self.home / "Git" / "toolbox", HOME_ID)
        self.near = self.clone(self.home / "work" / "toolbox", WORK)

    def run_git(self, cwd: Path, *args: str) -> str:
        out = subprocess.run(["git", *args], cwd=cwd, env=self.env, capture_output=True, text=True, check=True)
        return out.stdout.strip()

    def clone(self, path: Path, ident: tuple[str, str]) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.run_git(self.tmp, "clone", "-q", str(self.origin), str(path))
        self.run_git(path, "config", "user.name", ident[0])
        self.run_git(path, "config", "user.email", ident[1])
        return path

    def commit(self, repo: Path, name: str, text: str, message: str) -> None:
        (repo / name).write_text(text)
        self.run_git(repo, "add", name)
        self.run_git(repo, "commit", "-q", "-m", message)

    def relay(self, *args: str) -> subprocess.CompletedProcess:
        argv = [sys.executable, str(SCRIPT), "--host", "far", "--repo", "Git/toolbox", "-y", *args]
        return subprocess.run(argv, cwd=self.near, env=self.env, capture_output=True, text=True)

    def origin_log(self) -> list[str]:
        return self.run_git(self.origin, "log", "--format=%s|%an <%ae>", "main").splitlines()

    def test_commits_land_under_the_far_identity(self):
        self.run_git(self.near, "checkout", "-q", "-b", "feat")
        self.commit(self.near, "b.txt", "two\n", "add b")
        self.commit(self.near, "c.txt", "three\n", "add c")
        result = self.relay()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.origin_log(),
            ["add c|Home Account <home@example.com>", "add b|Home Account <home@example.com>", "seed|Home Account <home@example.com>"],
        )

    def test_near_side_ends_on_pushed_main(self):
        self.run_git(self.near, "checkout", "-q", "-b", "feat")
        self.commit(self.near, "b.txt", "two\n", "add b")
        self.assertEqual(self.relay().returncode, 0)
        self.assertEqual(self.run_git(self.near, "rev-parse", "--abbrev-ref", "HEAD"), "main")
        self.assertEqual(self.run_git(self.near, "rev-parse", "main"), self.run_git(self.origin, "rev-parse", "main"))
        self.assertEqual(self.run_git(self.near, "branch", "--list", "feat"), "")

    def test_relay_from_main_works(self):
        self.commit(self.near, "b.txt", "two\n", "add b")
        self.assertEqual(self.relay().returncode, 0)
        self.assertEqual(self.run_git(self.near, "rev-parse", "main"), self.run_git(self.origin, "rev-parse", "main"))

    def test_lands_on_top_of_newer_origin(self):
        self.commit(self.far, "z.txt", "far\n", "far change")
        self.run_git(self.far, "push", "-q", "origin", "main")
        self.commit(self.near, "b.txt", "two\n", "add b")
        self.assertEqual(self.relay().returncode, 0)
        self.assertEqual([line.split("|")[0] for line in self.origin_log()], ["add b", "far change", "seed"])
        self.assertTrue((self.near / "z.txt").exists())

    def test_conflict_changes_nothing(self):
        self.commit(self.far, "a.txt", "far edit\n", "far edit")
        self.run_git(self.far, "push", "-q", "origin", "main")
        self.commit(self.near, "a.txt", "near edit\n", "near edit")
        before = self.run_git(self.near, "rev-parse", "HEAD")
        result = self.relay()
        self.assertEqual(result.returncode, 1)
        self.assertIn("conflict", result.stderr)
        self.assertEqual([line.split("|")[0] for line in self.origin_log()], ["far edit", "seed"])
        self.assertEqual(self.run_git(self.near, "rev-parse", "HEAD"), before)
        self.assertEqual(self.run_git(self.far, "status", "--porcelain"), "")

    def test_far_checkout_is_untouched(self):
        self.run_git(self.far, "checkout", "-q", "-b", "far-work")
        (self.far / "a.txt").write_text("uncommitted\n")
        self.commit(self.near, "b.txt", "two\n", "add b")
        self.assertEqual(self.relay().returncode, 0)
        self.assertEqual(self.run_git(self.far, "rev-parse", "--abbrev-ref", "HEAD"), "far-work")
        self.assertEqual((self.far / "a.txt").read_text(), "uncommitted\n")
        self.assertEqual(self.run_git(self.far, "worktree", "list").count("\n"), 0)

    def test_clean_far_main_is_fast_forwarded(self):
        self.commit(self.near, "b.txt", "two\n", "add b")
        result = self.relay()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("updated ~/Git/toolbox", result.stderr)
        self.assertEqual(self.run_git(self.far, "rev-parse", "main"), self.run_git(self.origin, "rev-parse", "main"))

    def test_dirty_far_main_is_left_alone(self):
        (self.far / "a.txt").write_text("uncommitted\n")
        self.commit(self.near, "b.txt", "two\n", "add b")
        before = self.run_git(self.far, "rev-parse", "main")
        result = self.relay()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("as it was", result.stderr)
        self.assertEqual(self.run_git(self.far, "rev-parse", "main"), before)
        self.assertEqual((self.far / "a.txt").read_text(), "uncommitted\n")

    def test_far_unpushed_commits_stay_unpushed(self):
        self.commit(self.far, "f.txt", "far only\n", "far unpushed")
        self.commit(self.near, "b.txt", "two\n", "add b")
        self.assertEqual(self.relay().returncode, 0)
        self.assertEqual([line.split("|")[0] for line in self.origin_log()], ["add b", "seed"])
        self.assertEqual(self.run_git(self.far, "log", "-1", "--format=%s", "main"), "far unpushed")

    def test_nearby_upstream_edit_still_finishes(self):
        self.commit(self.far, "a.txt", "one\nx\ny\nz\n", "grow a")
        self.run_git(self.far, "push", "-q", "origin", "main")
        self.run_git(self.near, "pull", "-q", "origin", "main")
        self.commit(self.far, "a.txt", "ONE\nx\ny\nz\n", "far edits line 1")
        self.run_git(self.far, "push", "-q", "origin", "main")
        self.commit(self.near, "a.txt", "one\nx\ny\nZ\n", "near edits line 4")
        result = self.relay()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.near / "a.txt").read_text(), "ONE\nx\ny\nZ\n")

    def test_failed_push_pushes_nothing(self):
        hook = self.far / ".git" / "hooks" / "pre-push"
        hook.write_text("#!/bin/sh\necho hook says no >&2\nexit 1\n")
        hook.chmod(0o755)
        self.commit(self.near, "b.txt", "two\n", "add b")
        before = self.run_git(self.near, "rev-parse", "HEAD")
        result = self.relay()
        self.assertEqual(result.returncode, 1)
        self.assertIn("hook says no", result.stderr)
        self.assertIn("nothing was pushed", result.stderr)
        self.assertEqual(len(self.origin_log()), 1)
        self.assertEqual(self.run_git(self.near, "rev-parse", "HEAD"), before)
        self.assertEqual(self.run_git(self.far, "rev-parse", "main"), self.run_git(self.origin, "rev-parse", "main"))

    def test_merge_commits_are_refused(self):
        self.run_git(self.near, "checkout", "-q", "-b", "side")
        self.commit(self.near, "s.txt", "side\n", "side")
        self.run_git(self.near, "checkout", "-q", "main")
        self.commit(self.near, "b.txt", "two\n", "add b")
        self.run_git(self.near, "merge", "-q", "--no-edit", "side")
        result = self.relay()
        self.assertEqual(result.returncode, 1)
        self.assertIn("merge commits", result.stderr)

    def test_empty_commits_are_refused(self):
        self.run_git(self.near, "commit", "-q", "--allow-empty", "-m", "empty")
        result = self.relay()
        self.assertEqual(result.returncode, 1)
        self.assertIn("empty commits", result.stderr)

    def test_work_email_in_message_is_refused(self):
        (self.near / "b.txt").write_text("two\n")
        self.run_git(self.near, "add", "b.txt")
        self.run_git(self.near, "commit", "-q", "-m", f"add b\n\nSigned-off-by: W <{WORK[1]}>")
        result = self.relay()
        self.assertEqual(result.returncode, 1)
        self.assertIn("reword it first", result.stderr)
        self.assertEqual(len(self.origin_log()), 1)

    def test_other_branch_target(self):
        self.run_git(self.far, "push", "-q", "origin", "main:dev")
        self.run_git(self.near, "fetch", "-q", "origin")
        self.run_git(self.near, "checkout", "-q", "-b", "dev", "origin/dev")
        self.commit(self.near, "b.txt", "two\n", "add b")
        self.assertEqual(self.relay("--branch", "dev").returncode, 0)
        self.assertEqual(self.run_git(self.origin, "log", "-1", "--format=%s", "dev"), "add b")
        self.assertEqual(len(self.origin_log()), 1)

    def test_dirty_near_side_is_refused(self):
        self.commit(self.near, "b.txt", "two\n", "add b")
        (self.near / "b.txt").write_text("edited\n")
        result = self.relay()
        self.assertEqual(result.returncode, 1)
        self.assertIn("commit them first", result.stderr)
        self.assertEqual(len(self.origin_log()), 1)

    def test_ssh_failure_names_the_fix(self):
        self.commit(self.near, "b.txt", "two\n", "add b")
        self.env["RELAY_SSH"] = "sh -c 'echo Permission denied >&2; exit 255'"
        result = self.relay()
        self.assertEqual(result.returncode, 1)
        self.assertIn("wrong password", result.stderr)
        self.assertEqual(len(self.origin_log()), 1)

    def test_far_commit_hooks_are_skipped(self):
        hook = self.far / ".git" / "hooks" / "pre-commit"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        self.commit(self.near, "b.txt", "two\n", "add b")
        result = self.relay()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.origin_log()[0], "add b|Home Account <home@example.com>")

    def test_nothing_to_relay(self):
        result = self.relay()
        self.assertEqual(result.returncode, 0)
        self.assertIn("Nothing to relay", result.stdout)

    def test_stray_main_commits_block_a_branch_relay(self):
        self.commit(self.near, "m.txt", "main only\n", "main only")
        self.run_git(self.near, "checkout", "-q", "-b", "feat", "origin/main")
        self.commit(self.near, "b.txt", "two\n", "add b")
        result = self.relay()
        self.assertEqual(result.returncode, 1)
        self.assertIn("relay from main", result.stderr)
        self.assertEqual(len(self.origin_log()), 1)


DUNGEON = "100.103.22.125"


def status(state: str = "Running", online: bool = True) -> dict:
    peer = {"HostName": "dungeon", "TailscaleIPs": [DUNGEON], "Online": online, "LastSeen": "2026-10-01T09:00:00Z"}
    return {"BackendState": state, "Peer": {"key": peer}}


class TailnetProblemTest(unittest.TestCase):
    def test_online_peer_is_fine(self):
        self.assertIsNone(relay_mod.tailnet_problem(status(), DUNGEON))

    def test_disconnected_says_connect(self):
        self.assertIn("not connected", relay_mod.tailnet_problem(status("Stopped"), DUNGEON))

    def test_logged_out_says_log_in(self):
        self.assertIn("log in", relay_mod.tailnet_problem(status("NeedsLogin"), DUNGEON))

    def test_offline_peer_is_named(self):
        problem = relay_mod.tailnet_problem(status(online=False), DUNGEON)
        self.assertIn("dungeon is offline", problem)
        self.assertIn("2026-10-01", problem)

    def test_unknown_ip_is_named(self):
        self.assertIn("not a device", relay_mod.tailnet_problem(status(), "100.1.2.3"))


class CheckTailnetTest(unittest.TestCase):
    def check(self, ip: str, tailscale: str) -> None:
        with mock.patch.object(relay_mod, "ssh_hostname", return_value=ip), mock.patch.dict(os.environ, {"RELAY_TAILSCALE": tailscale}):
            relay_mod.check_tailnet("dungeonts")

    def fake(self, payload: dict) -> str:
        return shlex.join([sys.executable, "-c", f"print({json.dumps(json.dumps(payload))})"])

    def test_lan_host_skips_tailscale(self):
        self.check("192.168.1.238", "/nonexistent/tailscale")

    def test_offline_peer_raises(self):
        with self.assertRaisesRegex(relay_mod.RelayError, "offline"):
            self.check(DUNGEON, self.fake(status(online=False)))

    def test_online_peer_passes(self):
        self.check(DUNGEON, self.fake(status()))

    def test_missing_cli_warns_and_continues(self):
        with mock.patch("sys.stderr") as err:
            self.check(DUNGEON, "/nonexistent/tailscale")
        self.assertIn("unchecked", "".join(c.args[0] for c in err.write.call_args_list))

    def test_daemon_down_says_start_it(self):
        with self.assertRaisesRegex(relay_mod.RelayError, "not running"):
            self.check(DUNGEON, "sh -c 'echo daemon down >&2'")


class SshFailureTest(unittest.TestCase):
    def test_known_failure_gets_a_hint(self):
        msg = relay_mod.ssh_failure("dungeonts", "ssh: connect to host 100.103.22.125 port 22: Operation timed out")
        self.assertIn("is it awake and on Tailscale", msg)

    def test_bad_password_says_so(self):
        self.assertIn("wrong password", relay_mod.ssh_failure("dungeonts", "Permission denied (publickey,password)."))

    def test_unknown_failure_is_passed_through(self):
        self.assertIn("weird", relay_mod.ssh_failure("dungeonts", "weird\n"))


class PickHostTest(unittest.TestCase):
    def pick(self, hosts: list[str], up: set[str]) -> str:
        with mock.patch.object(relay_mod, "reachable", side_effect=lambda h: h in up):
            return relay_mod.pick_host(hosts)

    def test_lan_first_when_up(self):
        self.assertEqual(self.pick(["dungeon", "dungeonts"], {"dungeon", "dungeonts"}), "dungeon")

    def test_falls_back_to_tailnet(self):
        self.assertEqual(self.pick(["dungeon", "dungeonts"], {"dungeonts"}), "dungeonts")

    def test_last_host_is_never_probed(self):
        self.assertEqual(self.pick(["dungeonts"], set()), "dungeonts")


if __name__ == "__main__":
    unittest.main()
