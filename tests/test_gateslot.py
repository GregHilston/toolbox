"""gateslot.py's wait log, its report, and the mark a whole clean gate leaves."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load

gateslot = load("gateslot.py")


def ticket(cwd: str, started: float, ended: float) -> str:
    return json.dumps({"kind": "ticket", "cwd": cwd, "issue": 1, "started": started, "ended": ended})


def gate(cwd: str, asked: float, got: float, land: bool = False) -> str:
    return json.dumps({"kind": "gate", "cwd": cwd, "land": land, "asked": asked, "got": got, "ended": got + 100})


class ReportTest(unittest.TestCase):
    def test_share_counts_only_waits_inside_that_lanes_tickets(self) -> None:
        lines = [ticket("/a", 0, 3600), ticket("/b", 0, 3600), gate("/a", 100, 460), gate("/b", 7000, 7600),
                 gate("/main", 200, 500, land=True)]
        out = gateslot.report(lines)
        self.assertIn("2 tickets in 1.0 h (2.0 an hour)", out)
        self.assertIn("gate wait 6 min of 120 min ticket time (5%)", out)
        self.assertIn("3 gates, 1 landing, landing wait 5 min", out)

    def test_since_drops_older_events(self) -> None:
        out = gateslot.report([ticket("/a", 0, 10), gate("/a", 1, 2)], since=100)
        self.assertEqual(out, "no tickets in the log; 0 gates")

    def test_gates_are_named_by_ticket_even_with_no_ticket_rows(self) -> None:
        rows = [json.loads(gate("/a", 0, 60)), json.loads(gate("/a", 200, 200, land=True)), json.loads(gate("/b", 0, 0))]
        rows[0]["ticket"] = rows[1]["ticket"] = "1564"
        out = gateslot.report([json.dumps(r) for r in rows])
        self.assertIn("no tickets in the log; 3 gates", out)
        self.assertIn("by ticket: #1564 2 gates (1 landing), wait 1 min, run 3 min", out)
        self.assertEqual(out.count("#"), 1, f"a ticketless gate was named: {out}")

    def test_an_int_ticket_names_its_gates(self) -> None:
        row = json.loads(gate("/a", 0, 0))
        row["ticket"] = 7
        self.assertIn("#7 1 gates (0 landing)", gateslot.report([json.dumps(row)]))


class Python39Test(unittest.TestCase):
    @unittest.skipUnless(Path("/usr/bin/python3").exists(), "no /usr/bin/python3")
    def test_gateslot_imports_on_the_system_python(self) -> None:
        out = subprocess.run(["/usr/bin/python3", "-c",
                              "import sys; sys.path.insert(0, sys.argv[1]); import gateslot",
                              str(Path(gateslot.__file__).parent)], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)


class SlotCase(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        for name, value in (("DIR", self.root), ("PASSED", self.root / "passed"), ("LOG", self.root / "log.jsonl")):
            patcher = mock.patch.object(gateslot, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        env = mock.patch.dict(os.environ, {"GATE_SLOTS": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                                            "RUN_LOG_DIR": str(self.root / "run-log")})
        env.start()
        self.addCleanup(env.stop)

    def test_slot_logs_when_it_asked_got_and_ended(self) -> None:
        with gateslot.slot():
            pass
        event = json.loads(gateslot.LOG.read_text())
        self.assertEqual(event["kind"], "gate", f"event {event}")
        self.assertLessEqual(event["asked"], event["got"], f"event {event}")
        self.assertLessEqual(event["got"], event["ended"], f"event {event}")

    def test_the_queue_being_off_writes_no_record(self) -> None:
        with mock.patch.dict(os.environ, {"GATE_SLOTS": "0"}):
            with gateslot.slot():
                pass
        self.assertFalse(gateslot.LOG.exists(), "GATE_SLOTS=0 still wrote a record")

    def repo(self) -> Path:
        repo = self.root / "repo"
        repo.mkdir()
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
        (repo / "verify.sh").write_text("#!/bin/sh\nexit 0\n")
        (repo / "verify.sh").chmod(0o755)
        subprocess.run([*git, "init", "-q"], cwd=repo, check=True)
        subprocess.run([*git, "add", "."], cwd=repo, check=True)
        subprocess.run([*git, "commit", "-qm", "seed"], cwd=repo, check=True)
        cwd = os.getcwd()
        os.chdir(repo)
        self.addCleanup(os.chdir, cwd)
        return repo

    def test_the_row_names_the_newest_unpushed_ticket_or_none(self) -> None:
        repo = self.repo()
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
        remote = self.root / "remote.git"
        subprocess.run([*git, "init", "-q", "--bare", str(remote)], check=True)
        subprocess.run([*git, "remote", "add", "origin", str(remote)], cwd=repo, check=True)
        for msg in ("feat: pushed (#5)", "push", "feat: older (#6)", "fix: newer (#9)", "chore: no ticket"):
            cmd = ["push", "-q", "origin", "HEAD:refs/heads/main"] if msg == "push" else \
                ["commit", "-q", "--allow-empty", "-m", msg]
            subprocess.run([*git, *cmd], cwd=repo, check=True)
        with mock.patch.dict(os.environ, {"RUN_LOG_TICKET": "77"}):
            gateslot.main(["--", "./verify.sh"])
        with mock.patch.dict(os.environ, {"RUN_LOG_TICKET": ""}):
            gateslot.main(["--", "./verify.sh"])
            subprocess.run([*git, "push", "-q", "origin", "HEAD:refs/heads/main"], cwd=repo, check=True)
            gateslot.main(["--", "./verify.sh"])
        rows = [json.loads(line) for line in gateslot.LOG.read_text().splitlines()]
        self.assertEqual([r.get("ticket") for r in rows], ["77", "9", None], rows)
        self.assertNotIn("ticket", rows[2], f"a pushed branch wrote a ticket key: {rows[2]}")

    def test_a_whole_gate_on_a_clean_tree_marks_it_passed(self) -> None:
        self.repo()
        self.assertEqual(gateslot.main(["--", "./verify.sh"]), 0)
        self.assertTrue(gateslot.already_passed(), "a whole clean gate left no mark")

    def test_a_partial_gate_or_a_dirty_tree_leaves_no_mark(self) -> None:
        repo = self.repo()
        gateslot.main(["--", "./verify.sh", "api"])
        self.assertFalse(gateslot.already_passed(), "a partial gate marked the tree")
        (repo / "dirty").write_text("x")
        gateslot.main(["--", "./verify.sh"])
        self.assertFalse(gateslot.already_passed(), "a dirty tree was marked")

    def test_the_gate_event_carries_the_tree_and_whether_the_whole_gate_ran(self) -> None:
        self.repo()
        runlog = load("runlog.py")
        runlog.start("tree")
        gateslot.main(["--", "./verify.sh"])
        gateslot.main(["--", "./verify.sh", "api"])
        done = [json.loads(line) for line in runlog.log_path("tree").read_text().splitlines()
                if '"gate_done"' in line]
        self.assertEqual([e["full"] for e in done], [True, False], done)
        self.assertEqual(done[0]["tree"], done[1]["tree"], done)
        self.assertEqual(len(done[0]["tree"]), 12, done)

    def test_a_failed_gate_leaves_no_mark(self) -> None:
        repo = self.repo()
        (repo / "verify.sh").write_text("#!/bin/sh\nexit 1\n")
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "red"],
                       cwd=repo, check=True)
        self.assertEqual(gateslot.main(["--", "./verify.sh"]), 1)
        self.assertFalse(gateslot.already_passed(), "a red gate marked the tree")


if __name__ == "__main__":
    unittest.main()
