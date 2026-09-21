"""Tests for `bin/agent-watch.py`.

The watcher reads three sources that all lie in their own way: a kanban.db being
written by a live dispatcher, a workspace an agent is midway through creating,
and oMLX counters that are global and cumulative rather than per-run. Each of
those is a way to render a wrong number confidently, so they are what is tested.
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
    def test_reports_the_runs_own_totals_not_the_servers(self):
        """oMLX's counters cover every model and every caller since it started,
        so a watcher that reads them straight attributes the whole day to one run."""
        baseline = {"m": {"requests": 100, "prompt_tokens": 1_000_000, "completion_tokens": 50_000,
                          "cached_tokens": 900_000, "prefill_duration": 500.0,
                          "generation_duration": 400.0}}
        now = {"m": {"requests": 110, "prompt_tokens": 1_400_000, "completion_tokens": 55_000,
                     "cached_tokens": 1_240_000, "prefill_duration": 600.0,
                     "generation_duration": 480.0}}
        line, = watch.model_lines(baseline, now, elapsed=300)
        self.assertIn("10 reqs (2.0/min)", line)
        self.assertIn("40.0k avg prompt", line)   # 400k new prompt over 10 requests
        self.assertIn("85% cached", line)         # 340k of 400k
        self.assertIn("prefill 10.0s/req", line)
        self.assertIn("5000 completion tokens", line)

    def test_a_model_with_no_new_traffic_is_omitted(self):
        """The judge serves nothing until a handoff; a '0 reqs' line every 20s
        would read as a broken configuration rather than an idle one."""
        same = {"m": {"requests": 7, "prompt_tokens": 10, "completion_tokens": 1,
                      "cached_tokens": 0, "prefill_duration": 1.0, "generation_duration": 1.0}}
        self.assertEqual(watch.model_lines(same, same, elapsed=60), [])

    def test_no_division_by_zero_before_the_first_request(self):
        baseline = {"m": {"requests": 0, "prompt_tokens": 0}}
        self.assertEqual(watch.model_lines(baseline, {"m": {"requests": 0}}, elapsed=0), [])


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
