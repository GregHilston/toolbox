"""pi-workers exists to name three absences, so that is what these test.

A worker that never started, one that died, and one that went quiet all look
identical to a human reading a log directory — and all three were misreported
as "still running" in the run this tooling came out of. The classification is
the whole product; everything else is presentation.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import io
import json
import os
import pathlib
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load


@contextlib.contextmanager
def stdin_of(text: str):
    """There is no contextlib.redirect_stdin, and --from-statusline reads one."""
    original = sys.stdin
    sys.stdin = io.StringIO(text)
    try:
        yield
    finally:
        sys.stdin = original

workers = load("pi-workers.py")

# pid 1 is launchd/init: always alive, and never ours, which also exercises the
# PermissionError branch of the liveness check.
ALIVE_PID = 1
# Above the pid_max of any platform we run on, so it cannot be reused mid-test.
DEAD_PID = 9_999_999


def ago(seconds: float) -> str:
    stamp = dt.datetime.now(dt.UTC) - dt.timedelta(seconds=seconds)
    return stamp.isoformat().replace("+00:00", "Z")


def write_worker(root: Path, name: str, status: dict | None) -> Path:
    """Provision a worker the way the orchestrator does.

    `guardrails.json` goes in before spawning (Step P1b-bis), which is what
    makes a worker that never wrote a status file still discoverable.
    """
    directory = root / "worktrees" / name
    (directory / ".pi").mkdir(parents=True, exist_ok=True)
    (directory / ".pi" / "guardrails.json").write_text("{}", encoding="utf-8")
    if status is not None:
        (directory / ".pi" / "status.json").write_text(json.dumps(status), encoding="utf-8")
    return directory


def working_status(**overrides) -> dict:
    status = {
        "phase": "tool",
        "pid": ALIVE_PID,
        "turn": 18,
        "toolCalls": 11,
        "currentTool": "bash",
        "lastToolBrief": "godot --headless",
        "lastActivityAt": ago(1),
        "blockedCount": 0,
        "recent": [],
        "usage": {"totalTokens": 51000, "costUsd": 0.0151},
    }
    status.update(overrides)
    return status


def snapshot(root: Path, stall_seconds: float = 120.0):
    found = workers.discover([root])
    return {w["name"]: w for w in workers.gather(found, stall_seconds)}


class Classification(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_a_pi_directory_with_no_status_file_never_started(self):
        # The spawn bug: the heredoc wrote, the harness reported the command as
        # running, and no process was ever created.
        write_worker(self.root, "issue-98", None)
        worker = snapshot(self.root)["issue-98"]
        self.assertEqual(worker["state"], "nostart")
        self.assertTrue(worker["needsAttention"])
        self.assertIn("never started", worker["doing"])

    def test_a_status_file_whose_process_is_gone_is_dead_not_slow(self):
        write_worker(self.root, "issue-97", working_status(pid=DEAD_PID))
        worker = snapshot(self.root)["issue-97"]
        self.assertEqual(worker["state"], "dead")
        self.assertTrue(worker["needsAttention"])

    def test_a_live_but_cold_worker_is_stalled(self):
        write_worker(self.root, "issue-96", working_status(phase="thinking", lastActivityAt=ago(600)))
        worker = snapshot(self.root)["issue-96"]
        self.assertEqual(worker["state"], "stalled")
        self.assertIn("600s", worker["doing"])

    def test_death_outranks_staleness(self):
        # Both are true of a worker that died ten minutes ago. "dead" is the
        # actionable one: no amount of waiting fixes it.
        write_worker(self.root, "issue-95", working_status(pid=DEAD_PID, lastActivityAt=ago(600)))
        self.assertEqual(snapshot(self.root)["issue-95"]["state"], "dead")

    def test_a_finished_worker_is_done_even_though_its_process_is_gone(self):
        write_worker(self.root, "issue-64", working_status(phase="settled", pid=DEAD_PID))
        worker = snapshot(self.root)["issue-64"]
        self.assertEqual(worker["state"], "done", "settled means finished, not died")
        self.assertFalse(worker["needsAttention"])

    def test_shutdown_is_also_terminal(self):
        write_worker(self.root, "issue-65", working_status(phase="shutdown", pid=DEAD_PID))
        self.assertEqual(snapshot(self.root)["issue-65"]["state"], "done")

    def test_a_live_warm_worker_is_reported_as_working(self):
        write_worker(self.root, "issue-30", working_status())
        worker = snapshot(self.root)["issue-30"]
        self.assertEqual(worker["state"], "tool")
        self.assertFalse(worker["needsAttention"])
        self.assertIn("godot --headless", worker["doing"])

    def test_the_stall_threshold_is_configurable(self):
        write_worker(self.root, "issue-16", working_status(phase="thinking", lastActivityAt=ago(90)))
        self.assertEqual(snapshot(self.root, stall_seconds=120)["issue-16"]["state"], "thinking")
        self.assertEqual(snapshot(self.root, stall_seconds=60)["issue-16"]["state"], "stalled")

    def test_a_missing_pid_is_not_evidence_of_death(self):
        status = working_status()
        del status["pid"]
        write_worker(self.root, "issue-41", status)
        self.assertEqual(snapshot(self.root)["issue-41"]["state"], "tool")

    def test_a_missing_timestamp_is_not_evidence_of_a_stall(self):
        status = working_status()
        del status["lastActivityAt"]
        write_worker(self.root, "issue-42", status)
        worker = snapshot(self.root)["issue-42"]
        self.assertEqual(worker["state"], "tool")
        self.assertIsNone(worker["ageSeconds"])


class Robustness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_a_corrupt_status_file_says_so_rather_than_raising(self):
        directory = write_worker(self.root, "issue-99", None)
        (directory / ".pi" / "status.json").write_text("{not json", encoding="utf-8")
        worker = snapshot(self.root)["issue-99"]
        self.assertEqual(worker["state"], "unknown")
        self.assertTrue(worker["needsAttention"], "a file we cannot read is a thing to go look at")

    def test_a_status_file_holding_a_json_scalar_is_handled(self):
        directory = write_worker(self.root, "issue-88", None)
        (directory / ".pi" / "status.json").write_text("42", encoding="utf-8")
        self.assertEqual(snapshot(self.root)["issue-88"]["state"], "unknown")

    def test_an_unparseable_timestamp_does_not_raise(self):
        write_worker(self.root, "issue-87", working_status(lastActivityAt="not-a-time"))
        self.assertEqual(snapshot(self.root)["issue-87"]["state"], "tool")

    def test_a_naive_timestamp_is_read_as_utc_rather_than_crashing(self):
        # The extension always writes toISOString(), so this means a hand-edited
        # or foreign file. Subtracting a naive stamp from an aware `now` raises
        # TypeError, which would take down the whole table over one bad file.
        naive = (dt.datetime.now(dt.UTC) - dt.timedelta(seconds=600)).replace(tzinfo=None)
        write_worker(
            self.root,
            "issue-86",
            working_status(phase="thinking", lastActivityAt=naive.isoformat()),
        )
        worker = snapshot(self.root)["issue-86"]
        self.assertEqual(worker["state"], "stalled")
        self.assertGreater(worker["ageSeconds"], 500)

    def test_a_non_numeric_cost_does_not_crash_the_report(self):
        # Every number here is either formatted with `:.4f` or summed, so a
        # string where a float belongs raises — and takes the whole table, and
        # the status line with it, down over one malformed file.
        write_worker(self.root, "issue-85", working_status(usage={"costUsd": "0.03"}))
        write_worker(self.root, "issue-84", working_status())
        found = list(snapshot(self.root).values())
        self.assertIsNone(snapshot(self.root)["issue-85"]["costUsd"])
        table = workers.render_table(found, 200)
        self.assertIn("issue-85", table)
        self.assertIn("issue-84", table, "one bad file must not hide the healthy workers")
        self.assertIn("$0.0151", workers.render_oneline(found), "and the total still adds up")

    def test_a_boolean_is_not_mistaken_for_a_number(self):
        # bool is an int subclass, so a naive isinstance check renders `$1.0000`.
        write_worker(self.root, "issue-83", working_status(usage={"costUsd": True}))
        self.assertIsNone(snapshot(self.root)["issue-83"]["costUsd"])

    def test_process_alive_reports_unknown_rather_than_guessing(self):
        self.assertIsNone(workers.process_alive(None))
        self.assertIsNone(workers.process_alive(0))
        self.assertIsNone(workers.process_alive("51035"))
        self.assertIs(workers.process_alive(os.getpid()), True)
        self.assertIs(workers.process_alive(DEAD_PID), False)


class Discovery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_a_directory_without_a_pi_subdirectory_is_not_a_worker(self):
        (self.root / "worktrees" / "not-a-worker").mkdir(parents=True)
        write_worker(self.root, "issue-16", working_status())
        self.assertEqual([p.name for p in workers.discover([self.root])], ["issue-16"])

    def test_a_bare_pi_directory_is_not_a_worker(self):
        # `~/.pi` is pi's own configuration directory. Treating "has a .pi/" as
        # the test reported $HOME as a worker that never started — and because
        # the status line runs from whatever the session's cwd is, that showed
        # up as a permanent phantom `⚠1 nostart` in the bar.
        (self.root / "worktrees" / "looks-like-home" / ".pi" / "agent").mkdir(parents=True)
        self.assertEqual(workers.discover([self.root]), [])

    def test_a_provisioned_worker_that_never_started_is_still_found(self):
        # guardrails.json is written before spawning, so this is the nostart
        # case — the one the whole tool exists to name. Narrowing discovery must
        # not lose it.
        directory = self.root / "worktrees" / "issue-98"
        (directory / ".pi").mkdir(parents=True)
        (directory / ".pi" / "guardrails.json").write_text("{}", encoding="utf-8")
        self.assertEqual([p.name for p in workers.discover([self.root])], ["issue-98"])
        self.assertEqual(snapshot(self.root)["issue-98"]["state"], "nostart")

    def test_the_root_itself_counts_when_it_is_the_worker(self):
        # `--root <worktree>` should report that worktree, not nothing.
        (self.root / ".pi").mkdir()
        (self.root / ".pi" / "status.json").write_text(json.dumps(working_status()))
        self.assertIn(self.root, workers.discover([self.root]))

    def test_a_directory_reachable_twice_is_only_reported_once(self):
        write_worker(self.root, "issue-16", working_status())
        found = workers.discover([self.root, self.root])
        self.assertEqual(len(found), 1, "two roots pointing at one worker is still one worker")


class Rendering(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_oneline_is_empty_when_nothing_is_running(self):
        # The status-bar widget hides itself on empty output, so this is what
        # keeps it invisible in every session that is not orchestrating.
        self.assertEqual(workers.render_oneline([]), "")

    def test_oneline_is_empty_once_every_worker_has_finished_cleanly(self):
        write_worker(self.root, "issue-64", working_status(phase="settled"))
        self.assertEqual(workers.render_oneline(list(snapshot(self.root).values())), "")

    def test_oneline_still_speaks_up_when_a_finished_run_left_trouble(self):
        write_worker(self.root, "issue-64", working_status(phase="settled"))
        write_worker(self.root, "issue-97", working_status(pid=DEAD_PID))
        line = workers.render_oneline(list(snapshot(self.root).values()))
        self.assertIn("⚠1 dead", line, "a dead worker must not be hidden by a finished one")

    def test_oneline_totals_cost_across_workers(self):
        write_worker(self.root, "issue-30", working_status())
        write_worker(self.root, "issue-41", working_status())
        line = workers.render_oneline(list(snapshot(self.root).values()))
        self.assertIn("$0.0302", line)
        self.assertIn("2w", line)

    def test_the_table_lists_who_needs_attention(self):
        write_worker(self.root, "issue-97", working_status(pid=DEAD_PID))
        write_worker(self.root, "issue-30", working_status())
        table = workers.render_table(list(snapshot(self.root).values()), 200)
        self.assertIn("Needs attention: issue-97", table)
        self.assertNotIn("Needs attention: issue-30", table)

    def test_the_table_says_something_useful_when_there_are_no_workers(self):
        empty = workers.render_table([], 200)
        self.assertIn("No pi workers found", empty)
        # It must name the real rule. Saying "a directory containing .pi/" sent
        # anyone debugging a missing worker looking in the wrong place.
        for marker in workers.WORKER_MARKERS:
            self.assertIn(marker, empty)

    def test_table_rows_are_truncated_to_the_given_width(self):
        write_worker(self.root, "issue-30", working_status(lastToolBrief="x" * 400))
        rows = workers.render_table(list(snapshot(self.root).values()), 90).splitlines()
        self.assertTrue(all(len(row) <= 90 for row in rows))


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def run_cli(self, *argv: str) -> int:
        """Swallow the rendering; these tests are about the exit code."""
        with contextlib.redirect_stdout(io.StringIO()):
            return workers.main(list(argv))

    def test_strict_exits_nonzero_only_when_something_needs_attention(self):
        write_worker(self.root, "issue-30", working_status())
        self.assertEqual(self.run_cli("--root", str(self.root), "--json", "--strict"), 0)
        write_worker(self.root, "issue-97", working_status(pid=DEAD_PID))
        self.assertEqual(self.run_cli("--root", str(self.root), "--json", "--strict"), 1)

    def test_strict_exits_two_when_it_finds_nothing_at_all(self):
        self.assertEqual(self.run_cli("--root", str(self.root), "--json", "--strict"), 2)

    def test_without_strict_the_exit_code_stays_zero(self):
        # The status bar renders `[Exit: N]` for a non-zero exit, so the mode it
        # uses must never signal through one.
        write_worker(self.root, "issue-97", working_status(pid=DEAD_PID))
        self.assertEqual(self.run_cli("--root", str(self.root), "--oneline"), 0)

    def test_explicit_paths_skip_discovery(self):
        directory = write_worker(self.root, "issue-30", working_status())
        with contextlib.redirect_stdout(io.StringIO()) as captured:
            workers.main([str(directory), "--json"])
        self.assertEqual([w["name"] for w in json.loads(captured.getvalue())], ["issue-30"])

    def test_from_statusline_takes_its_root_from_the_payload(self):
        write_worker(self.root, "issue-30", working_status())
        with contextlib.redirect_stdout(io.StringIO()) as captured:
            with stdin_of(json.dumps({"cwd": str(self.root)})):
                workers.main(["--from-statusline", "--oneline"])
        self.assertIn("pi 1w", captured.getvalue())

    def test_from_statusline_survives_a_payload_it_cannot_parse(self):
        # A broken payload must render an empty widget, never an error message
        # pinned to the status bar. `--root` is pinned at an empty directory so
        # the assertion is about the payload and not about whatever the test
        # runner's cwd happens to contain.
        with contextlib.redirect_stdout(io.StringIO()) as captured:
            with stdin_of("not json"):
                exit_code = workers.main(
                    ["--from-statusline", "--oneline", "--root", str(self.root)]
                )
        self.assertEqual(exit_code, 0)
        self.assertEqual(captured.getvalue(), "")


if __name__ == "__main__":
    unittest.main()

def _worker_from_usage(usage):
    """Read one worker whose status file carries exactly this usage block."""
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp) / "issue-1"
        (d / ".pi").mkdir(parents=True)
        (d / ".pi" / "status.json").write_text(
            json.dumps({"phase": "thinking", "pid": os.getpid(), "turn": 1, "usage": usage})
        )
        return workers.read_worker(d, dt.datetime.now(dt.timezone.utc), 120.0)


class TestCostAndCacheHit(unittest.TestCase):
    """pi's own cost number is stale, so the table must not show it uncritically.

    DeepSeek repriced on 2026-08-16; pi 0.84.3's catalog predates that and
    under-reports by roughly 3x. The orchestration-status extension prices each
    turn itself into `costRealUsd`, and that is what a human should be reading.
    """

    def test_prefers_the_real_cost_over_pi_s_reported_one(self):
        usage = {"costUsd": 1.62, "costRealUsd": 4.87, "cacheRead": 99, "input": 1}
        worker = _worker_from_usage(usage)
        self.assertAlmostEqual(worker["costRealUsd"], 4.87)

    def test_falls_back_to_pi_s_number_for_an_older_status_file(self):
        """A worker started before the extension was updated still renders."""
        worker = _worker_from_usage({"costUsd": 0.5})
        self.assertAlmostEqual(worker["costRealUsd"], 0.5)

    def test_hit_pct_is_the_share_of_input_served_from_cache(self):
        self.assertAlmostEqual(workers.hit_pct({"cacheRead": 99, "input": 1}), 99.0)
        self.assertAlmostEqual(workers.hit_pct({"cacheRead": 0, "input": 10}), 0.0)

    def test_hit_pct_says_nothing_rather_than_dividing_by_zero(self):
        self.assertIsNone(workers.hit_pct({}), "a worker with no usage yet")
        self.assertIsNone(workers.hit_pct({"cacheRead": 0, "input": 0}), "or one with zero of both")

