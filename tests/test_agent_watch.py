"""Tests for `bin/agent-watch.py`.

The watcher reads three sources that all lie in their own way: a kanban.db being
written by a live dispatcher, a workspace an agent is midway through creating,
and an oMLX log that covers every model and every caller since the server
started. Each is a way to render a wrong number confidently, so they are what is
tested.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from _loader import load

watch = load("agent-watch.py")


def make_board(instance: Path, *, events, run=None, status="running") -> None:
    home = instance / "home"
    home.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(home / "kanban.db")
    conn.executescript(
        """
        create table tasks (id text, title text, status text);
        create table task_runs (id integer, task_id text, profile text, status text,
            started_at integer, last_heartbeat_at integer, outcome text, error text);
        create table task_events (id integer primary key, task_id text, run_id integer,
            kind text, payload text, created_at integer);
        """
    )
    conn.execute("insert into tasks values (?,?,?)", ("t_1", "build a thing", status))
    if run:
        conn.execute("insert into task_runs values (?,?,?,?,?,?,?,?)", run)
    for i, (kind, payload, created) in enumerate(events, start=1):
        conn.execute("insert into task_events values (?,?,?,?,?,?)",
                     (i, "t_1", 1, kind, payload, created))
    conn.commit()
    conn.close()


class Ago(unittest.TestCase):
    def test_units(self):
        self.assertEqual(watch.ago(9), "9s")
        self.assertEqual(watch.ago(75), "1m15s")
        self.assertEqual(watch.ago(3 * 3600 + 4 * 60), "3h04m")

    def test_clock_skew_does_not_render_negative(self):
        """started_at comes from inside the container; a skewed clock read as
        '-12s ago' looks like a bug in the run rather than in the clock."""
        self.assertEqual(watch.ago(-12), "0s")


class ModelLines(unittest.TestCase):
    def test_reports_per_model_totals(self):
        traffic = {"m": {"reqs": 10, "prompt": 400_000, "completion": 5_000, "secs": 180.0}}
        line, = watch.model_lines(traffic, elapsed=300)
        self.assertIn("10 reqs (2.0/min)", line)
        self.assertIn("40.0k avg prompt", line)
        self.assertIn("500 avg completion", line)
        self.assertIn("180s of model time", line)

    def test_a_model_with_no_traffic_is_omitted(self):
        """The judge serves nothing until a handoff; a '0 reqs' line every 20s
        would read as a broken configuration rather than an idle one."""
        self.assertEqual(watch.model_lines({"m": {"reqs": 0, "prompt": 0,
                                                  "completion": 0, "secs": 0.0}}, 60), [])

    def test_no_division_by_zero_before_the_first_request(self):
        self.assertEqual(watch.model_lines({}, elapsed=0), [])


class LogTraffic(unittest.TestCase):
    """oMLX's log is the source because stats.json lags unboundedly."""

    def _write(self, lines):
        fh = tempfile.NamedTemporaryFile("w", suffix=".log", delete=False)
        fh.write("".join(lines)); fh.close()
        watch.OMLX_LOG = Path(fh.name)
        return fh.name

    def test_counts_only_completions_after_the_run_started(self):
        fmt = ("{} - omlx.server - INFO - Chat completion: model={}, {} tokens "
               "in {}s (1 tok/s), prompt: {}, finish_reason=stop\n")
        self._write([
            fmt.format("2026-09-21 09:00:00,001", "M", 100, "5.0", 1000),   # before
            fmt.format("2026-09-21 10:00:05,001", "M", 200, "7.0", 2000),   # after
            fmt.format("2026-09-21 10:00:09,001", "M", 300, "8.0", 4000),   # after
            "2026-09-21 10:00:10,001 - omlx.scheduler - INFO - unrelated\n",
        ])
        start = time.mktime(time.strptime("2026-09-21 10:00:00", "%Y-%m-%d %H:%M:%S"))
        got = watch.log_traffic(start)
        self.assertEqual(got["M"]["reqs"], 2)
        self.assertEqual(got["M"]["prompt"], 6000)
        self.assertEqual(got["M"]["completion"], 500)
        self.assertAlmostEqual(got["M"]["secs"], 15.0)

    def test_a_missing_log_is_not_an_error(self):
        watch.OMLX_LOG = Path("/nonexistent/omlx.log")
        self.assertEqual(watch.log_traffic(time.time()), {})


class LastCompletion(unittest.TestCase):
    """The stall warning is the one thing the watcher exists for, and run
    gate-a showed what it costs to miss: heartbeats for 51 minutes with no
    model traffic for twenty of them, and nothing anywhere noticed."""

    FMT = ("{} - omlx.server - INFO - Chat completion: model=M, 10 tokens "
           "in 1.0s (1 tok/s), prompt: 100, finish_reason=stop\n")

    def _write(self, lines):
        fh = tempfile.NamedTemporaryFile("w", suffix=".log", delete=False)
        fh.write("".join(lines)); fh.close()
        watch.OMLX_LOG = Path(fh.name)

    def _at(self, stamp):
        return time.mktime(time.strptime(stamp, "%Y-%m-%d %H:%M:%S"))

    def test_returns_the_most_recent_completion(self):
        self._write([self.FMT.format("2026-09-21 10:00:05,001"),
                     self.FMT.format("2026-09-21 10:07:30,001")])
        got = watch.last_completion(self._at("2026-09-21 10:00:00"))
        self.assertEqual(got, self._at("2026-09-21 10:07:30"))

    def test_a_completion_before_the_run_does_not_count(self):
        """Otherwise a quiet run inherits the previous run's last request and
        reads as busy -- the log is one unrotated file spanning weeks."""
        self._write([self.FMT.format("2026-09-21 09:00:00,001")])
        start = self._at("2026-09-21 10:00:00")
        self.assertEqual(watch.last_completion(start), start)

    def test_silence_since_the_run_started_reports_the_start(self):
        self._write([])
        start = self._at("2026-09-21 10:00:00")
        self.assertEqual(watch.last_completion(start), start)

    def test_a_missing_log_does_not_raise(self):
        watch.OMLX_LOG = Path("/nonexistent/omlx.log")
        start = time.time()
        self.assertEqual(watch.last_completion(start), start)


class WorkspaceState(unittest.TestCase):
    def test_excludes_the_venv(self):
        """`uv sync` drops ~24 packages of Python into .venv/. Counted, the
        workspace reads as thousands of files the agent did not write."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "workspace"
            (ws / "src/vt_smb").mkdir(parents=True)
            (ws / ".venv/lib/python3.13/site-packages/pandas").mkdir(parents=True)
            (ws / "src/vt_smb/cli.py").write_text("import click\n\n\nmain = None\n")
            (ws / ".venv/lib/python3.13/site-packages/pandas/__init__.py").write_text("x = 1\n")
            state = watch.workspace_state(Path(tmp))
            self.assertEqual(state["files"], 1)
            self.assertEqual(state["loc"], 2)        # blank lines are not code
            self.assertEqual(str(state["newest_path"]), "src/vt_smb/cli.py")

    def test_missing_workspace_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(watch.workspace_state(Path(tmp))["files"], 0)


class Render(unittest.TestCase):
    def test_surfaces_the_latest_heartbeat_note(self):
        now = int(time.time())
        with tempfile.TemporaryDirectory() as tmp:
            instance = Path(tmp) / "seeded-a"
            make_board(
                instance,
                run=(1, "t_1", "builder", "running", now - 300, now - 20, None, None),
                events=[
                    ("created", None, now - 310),
                    ("heartbeat", json.dumps({"note": "planning the mapper"}), now - 200),
                    ("heartbeat", json.dumps({"note": "writing tests"}), now - 100),
                    ("heartbeat", None, now - 20),
                ],
            )
            out = watch.render(instance)
        self.assertIn("card=running", out)
        self.assertIn("elapsed 5m00s", out)
        # The most recent note, not the first one found scanning forwards.
        self.assertIn("writing tests", out)
        self.assertNotIn("planning the mapper", out)

    def test_reports_a_blocked_card_and_its_error(self):
        now = int(time.time())
        with tempfile.TemporaryDirectory() as tmp:
            instance = Path(tmp) / "seeded-b"
            make_board(
                instance,
                status="blocked",
                run=(1, "t_1", "builder", "failed", now - 600, now - 30,
                     "blocked", "turn budget exhausted"),
                events=[("created", None, now - 610), ("blocked", None, now - 30)],
            )
            out = watch.render(instance)
        self.assertIn("card=blocked", out)
        self.assertIn("turn budget exhausted", out)
        self.assertIn("events: created, blocked", out)

    def test_a_board_that_does_not_exist_yet(self):
        """The container spends its first seconds installing the firewall; the
        watcher is expected to be run immediately after launching a run."""
        with tempfile.TemporaryDirectory() as tmp:
            instance = Path(tmp) / "not-started"
            instance.mkdir()
            self.assertIn("card=?", watch.render(instance))


if __name__ == "__main__":
    unittest.main()
