"""runlog.py's append-only events, and run-report.py's split of a ticket's time."""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import BIN, load

runlog = load("runlog.py")
report = load("run-report.py")
REPO = BIN.parent


def event(t: float, name: str, **fields) -> dict:
    return {"t": t, "kind": name, "lane": fields.pop("lane", "b"),
            "ticket": fields.pop("ticket", None), "worktree": "/wt", **fields}


T0 = 1_000_000.0
FAKE = [
    event(T0 + 0, "ticket_start", ticket="1"),
    event(T0 + 0, "phase_start", ticket="1", phase="plan"),
    event(T0 + 300, "phase_end", ticket="1", phase="plan"),
    event(T0 + 300, "phase_start", ticket="1", phase="worker"),
    event(T0 + 1200, "test_run", ticket="1", seconds=200),
    event(T0 + 1500, "phase_end", ticket="1", phase="worker"),
    event(T0 + 1500, "gate_queued", ticket="1", land=False, gate_kind="worker"),
    event(T0 + 1620, "gate_slot", ticket="1", land=False, gate_kind="worker"),
    event(T0 + 1920, "gate_done", ticket="1", exit=0, gate_kind="worker"),
    event(T0 + 1920, "phase_start", ticket="1", phase="review"),
    event(T0 + 2220, "phase_end", ticket="1", phase="review"),
    event(T0 + 2220, "phase_start", ticket="1", phase="fix"),
    event(T0 + 2700, "test_run", ticket="1", seconds=180),
    event(T0 + 2700, "phase_end", ticket="1", phase="fix"),
    event(T0 + 2700, "gate_queued", ticket="1", land=False),
    event(T0 + 2760, "gate_slot", ticket="1", land=False),
    event(T0 + 3000, "gate_done", ticket="1", exit=0),
    event(T0 + 3000, "ticket_done", ticket="1", seconds=3000),
    event(T0 + 3000, "land_start"),
    event(T0 + 3600, "land_done", ok=True),
    event(T0 + 60, "wake", why="gate slot"),
    event(T0 + 90, "gate_skipped", gate_kind="baseline"),
    event(T0 + 120, "gate_lane", cached=True, seconds=600),
    event(T0 + 180, "gate_lane", cached=False, seconds=400),
    event(T0 + 30, "machine", load1=4.0, ram_free_mb=3000, cpu={"pi": 50.0}),
]


class Case(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        saved = {k: os.environ.pop(k) for k in list(os.environ) if k.startswith("RUN_LOG_")}
        self.addCleanup(os.environ.update, saved)
        os.environ["RUN_LOG_DIR"] = str(self.root / "logs")
        cwd = os.getcwd()
        os.chdir(REPO)  # a real git remote, so repo_name() resolves
        self.addCleanup(os.chdir, cwd)

    def lines(self, run: str) -> list[dict]:
        return [json.loads(line) for line in runlog.log_path(run).read_text().splitlines()]


class EmitTest(Case):
    def test_no_current_run_does_nothing(self) -> None:
        runlog.emit("tick", n=1)
        found = list((self.root / "logs").rglob("*.jsonl")) if (self.root / "logs").exists() else []
        self.assertEqual(found, [], "emit wrote without a current run")

    def test_an_unwritable_log_never_raises(self) -> None:
        path = runlog.start("blocked")
        path.mkdir()
        runlog.emit("tick")  # log path is a directory: open fails

    def test_lane_and_ticket_come_from_the_environment(self) -> None:
        runlog.start("env")
        os.environ["RUN_LOG_LANE"] = "lane-b"
        os.environ["RUN_LOG_TICKET"] = "7"
        runlog.emit("tick", n=1)
        line = self.lines("env")[0]
        self.assertEqual((line["lane"], line["ticket"], line["n"]), ("lane-b", "7", 1))

    def test_concurrent_emits_are_whole_lines(self) -> None:
        runlog.start("concurrent")
        cmd = [sys.executable, str(BIN / "runlog.py"), "emit", "tick"]
        procs = [subprocess.Popen([*cmd, f"i={i}"], cwd=REPO, env=os.environ.copy(),
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for i in range(8)]
        self.assertEqual([p.wait(timeout=60) for p in procs], [0] * 8)
        lines = self.lines("concurrent")
        self.assertEqual(len(lines), 8, f"got {len(lines)} lines")
        self.assertEqual(sorted(line["i"] for line in lines), list(range(8)))

    def test_sample_writes_a_machine_line_and_stops_on_a_new_run(self) -> None:
        runlog.start("sampling")

        def switch(_: float) -> None:
            (runlog.run_dir() / "current").write_text("later\n")

        with mock.patch.object(runlog.time, "sleep", side_effect=switch):
            self.assertEqual(runlog.sample(0), 0)
        lines = self.lines("sampling")
        self.assertEqual([line["kind"] for line in lines], ["machine"])
        self.assertIn("load1", lines[0])


PS = """ 600.0 /usr/bin/python3 -c import execnet.gateway_base
 400.0 /x/.venv/bin/python -m pytest -n 8 tests
  50.0 uv run pytest tests
  70.0 /usr/bin/python3 -u -c import sys;exec(eval(sys.stdin.readline()))
  25.0 python3 -c exec(eval(sys.stdin.read()))
  40.0 uv run build.py
  15.0 /x/bin/python /h/toolbox/bin/pi-ask.py --session s
 200.0 /Applications/Godot.app/Contents/MacOS/Godot --headless
  30.0 node /x/bin/pi --print
  20.0 /usr/bin/ssh dungeon
  10.0 /usr/bin/ssh dungeon
   5.0 /bin/zsh
   1.0 vim x
"""


class CpuTest(Case):
    def fake_ps(self) -> mock._patch:
        done = subprocess.CompletedProcess([], 0, stdout=PS)
        return mock.patch.object(runlog.subprocess, "run", return_value=done)

    def test_pytest_workers_and_children_are_named_by_their_args(self) -> None:
        top: dict[str, float] = {}
        with self.fake_ps():
            cpu = runlog.cpu_by_family(top)
        self.assertEqual(cpu["pytest"], 1120.0, cpu)
        self.assertEqual(cpu["godot"], 200.0, cpu)
        self.assertEqual(cpu["pi"], 30.0, cpu)
        self.assertEqual(cpu["other"], 116.0, cpu)

    def test_the_sample_lists_the_top_three_commands_inside_other(self) -> None:
        with self.fake_ps():
            machine = runlog.machine()
        self.assertEqual(list(machine["other_top"]), ["uv", "ssh", "python3"], machine)
        self.assertEqual(machine["other_top"]["uv"], 40.0)


class GateKindTest(Case):
    def test_a_plain_gate_is_a_worker_gate_and_a_landing_gate_stays_landing(self) -> None:
        gateslot = load("gateslot.py")
        os.environ["GATE_SLOT_DIR"] = str(self.root / "slots")
        runlog.start("kinds")
        for land in (False, True):
            with gateslot.slot(land=land):
                pass
        kinds = [e["gate_kind"] for e in self.lines("kinds") if e["kind"] == "gate_queued"]
        self.assertEqual(kinds, ["worker", "landing"])


class ReportTest(Case):
    def write(self, run: str) -> None:
        path = self.root / "logs" / "fakerepo" / f"{run}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(e) for e in FAKE) + "\n")

    def printed(self, *runs: str) -> str:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(report.main(list(runs)), 0)
        return out.getvalue()

    def test_a_ticket_splits_into_its_phases_with_almost_nothing_unexplained(self) -> None:
        self.write("r1")
        out = self.printed("r1")
        self.assertIn("LLM", out)
        self.assertIn("36%", out, out)   # 1300 s of plan and worker
        self.assertIn("11%", out, out)   # 380 s of own tests
        self.assertIn("5%", out, out)    # 180 s queueing for a gate
        self.assertIn("15%", out, out)   # 540 s of gate runs
        self.assertIn("17%", out, out)   # 600 s landing
        unexplained = next(line for line in out.splitlines() if line.startswith("unexplained"))
        self.assertLess(float(unexplained.split()[1].rstrip("%")), 5, out)

    def test_a_ticket_runs_through_its_landing_after_the_lane_stops(self) -> None:
        events = [
            event(T0, "ticket_start", ticket="7"),
            event(T0, "phase_start", ticket="7", phase="worker"),
            event(T0 + 600, "phase_end", ticket="7", phase="worker"),
            event(T0 + 600, "ticket_parked", ticket="7"),
            event(T0 + 700, "prep_start", ticket=None),
            event(T0 + 800, "review_start", ticket="7"),
            event(T0 + 1000, "fix_start", ticket="7"),
            event(T0 + 1200, "ready", ticket="7"),
            event(T0 + 1300, "land_start", ticket="7"),
            event(T0 + 1500, "land_done", ticket="7"),
            event(T0 + 1500, "landed", ticket="7"),
        ]
        summary = report.summarise(events)
        self.assertEqual(summary["total"], 1500, summary)
        shares = summary["shares"]
        self.assertEqual((shares["parked"], shares["prep"], shares["review"], shares["fix"]),
                         (100, 100, 200, 200), shares)
        self.assertEqual((shares["ready wait"], shares["landing"]), (100, 200), shares)
        self.assertLess(shares["unexplained"], 75, shares)

    def test_a_recovered_ticket_is_not_painted_parked(self) -> None:
        events = [
            event(T0, "ticket_start", ticket="7"),
            event(T0 + 100, "ticket_parked", ticket="7"),
            event(T0 + 300, "ticket_start", ticket="7"),
            event(T0 + 300, "phase_start", ticket="7", phase="worker"),
            event(T0 + 700, "phase_end", ticket="7", phase="worker"),
            event(T0 + 700, "ticket_done", ticket="7"),
        ]
        shares = report.summarise(events)["shares"]
        self.assertEqual((shares["parked"], shares["LLM"]), (200, 400), shares)
        self.assertEqual(shares["unexplained"], 100, shares)

    def test_an_untagged_landing_never_stretches_a_later_ticket(self) -> None:
        events = [
            event(T0, "ticket_start", ticket="7"),
            event(T0 + 100, "ticket_parked", ticket="7"),
            event(T0 + 150, "ticket_start", ticket="8"),
            event(T0 + 900, "land_start"),
            event(T0 + 1000, "land_done"),
            event(T0 + 1000, "ticket_done", ticket="8"),
        ]
        shares = report.summarise(events)["shares"]
        self.assertEqual(shares["landing"], 0, shares)
        self.assertEqual(shares["unexplained"], 950, shares)

    def test_a_recovery_after_another_ticket_does_not_overlap_it(self) -> None:
        events = [
            event(T0, "lane_start"),
            event(T0, "ticket_start", ticket="7"),
            event(T0 + 100, "ticket_parked", ticket="7"),
            event(T0 + 150, "ticket_start", ticket="8"),
            event(T0 + 400, "ticket_done", ticket="8"),
            event(T0 + 450, "ticket_start", ticket="7"),
            event(T0 + 600, "ticket_done", ticket="7"),
        ]
        summary = report.summarise(events)
        self.assertEqual(summary["total"], 550, summary)
        self.assertEqual(summary["no_ticket"], 50, summary)

    def test_resuming_while_another_row_is_open_does_not_overlap(self) -> None:
        events = [
            event(T0, "lane_start"),
            event(T0, "ticket_start", ticket="7"),
            event(T0 + 100, "ticket_parked", ticket="7"),
            event(T0 + 100, "ticket_start", ticket="8"),
            event(T0 + 150, "ticket_start", ticket="9"),
            event(T0 + 200, "ticket_start", ticket="7"),
            event(T0 + 300, "ticket_done", ticket="7"),
        ]
        self.assertEqual(report.summarise(events)["total"], 300)

    def test_a_stray_untagged_park_keeps_the_running_ticket_open(self) -> None:
        events = [
            event(T0, "ticket_start", ticket="8"),
            event(T0 + 200, "ticket_parked"),
            event(T0 + 500, "ticket_done", ticket="8"),
        ]
        self.assertEqual(report.summarise(events)["total"], 500)

    def test_hours_in_no_ticket_never_goes_negative_and_needs_a_worker_lane(self) -> None:
        events = [event(T0, "ticket_start", ticket="1"), event(T0 + 100, "ticket_done", ticket="1")]
        self.assertIsNone(report.summarise(events)["no_ticket"])
        overlap = [event(T0, "lane_start"), *events]
        self.assertEqual(report.summarise(overlap)["no_ticket"], 0)

    def test_an_untagged_prep_after_the_stop_counts_for_that_ticket(self) -> None:
        events = [
            event(T0, "ticket_start", ticket="7"),
            event(T0 + 100, "ticket_done", ticket="7"),
            event(T0 + 150, "prep_start"),
            event(T0 + 250, "review_start", ticket="7"),
            event(T0 + 300, "ready", ticket="7"),
        ]
        self.assertEqual(report.summarise(events)["shares"]["prep"], 100)

    def test_an_untagged_prep_needs_a_stopped_ticket(self) -> None:
        events = [
            event(T0, "ticket_start", ticket="7"),
            event(T0 + 100, "ticket_done", ticket="7"),
            event(T0 + 150, "ticket_start", ticket="8"),
            event(T0 + 200, "prep_start"),
            event(T0 + 400, "ticket_done", ticket="8"),
        ]
        self.assertEqual(report.summarise(events)["shares"]["prep"], 0)

    def test_an_untagged_park_does_not_close_a_later_ticket(self) -> None:
        events = [
            event(T0, "ticket_start", ticket="7"),
            event(T0 + 100, "ticket_done", ticket="7"),
            event(T0 + 120, "ticket_parked"),
            event(T0 + 150, "ticket_start", ticket="8"),
            event(T0 + 500, "ticket_done", ticket="8"),
        ]
        self.assertEqual(report.summarise(events)["total"], 450)

    def test_measured_gate_wait_outranks_the_ready_label(self) -> None:
        events = [
            event(T0, "ticket_start", ticket="7"),
            event(T0 + 10, "ticket_done", ticket="7"),
            event(T0 + 10, "ready", ticket="7"),
            event(T0 + 20, "gate_queued", ticket="7", land=True),
            event(T0 + 60, "gate_slot", ticket="7", land=True),
            event(T0 + 100, "land_start", ticket="7"),
            event(T0 + 110, "land_done", ticket="7"),
        ]
        shares = report.summarise(events)["shares"]
        self.assertEqual((shares["gate wait"], shares["ready wait"]), (40, 50), shares)

    def test_the_report_gives_unexplained_against_ticket_time_and_run_span(self) -> None:
        self.write("r1")
        out = self.printed("r1")
        self.assertIn("hours unexplained", out)
        self.assertIn("run span unexplained", out)

    def test_wakes_group_by_cause_not_by_lane(self) -> None:
        events = [event(T0, "wake", reason="a CONFLICT: see x"), event(T0 + 1, "wake", reason="b CONFLICT: y")]
        self.assertEqual(report.summarise(events)["wakes"], {"CONFLICT": 2})

    def test_the_summary_counts_gates_cache_wakes_and_skips(self) -> None:
        self.write("r1")
        out = self.printed("r1")
        lines = out.splitlines()

        def value(label: str) -> str:
            return next(line for line in lines if line.startswith(label + " ")).split()[-1]

        self.assertEqual(value("gates"), "2")
        self.assertEqual(value("cache skips"), "1")
        self.assertEqual(value("baseline skips"), "1")
        self.assertIn("10m", out)  # 600 s saved by a cached gate lane
        wake = next(line for line in lines if line.startswith("gate slot "))
        self.assertEqual(wake.split()[-1], "1")
        self.assertIn("load by hour", out)

    def test_samples_after_the_lanes_stop_do_not_stretch_the_run(self) -> None:
        events = [event(T0, "ticket_start", ticket="9"),
                  event(T0, "phase_start", ticket="9", phase="worker"),
                  event(T0 + 60, "phase_end", ticket="9", phase="worker"),
                  event(T0 + 7200, "machine", load1=1.0)]
        summary = report.summarise(events)
        self.assertEqual(summary["span"], 60)
        self.assertEqual(summary["shares"]["unexplained"], 0)

    def test_two_runs_share_one_table(self) -> None:
        self.write("r1")
        self.write("r2")
        out = self.printed("r1", "r2")
        header = next(line for line in out.splitlines() if "ticket time" in line)
        self.assertIn("r1", header)
        self.assertIn("r2", header)


if __name__ == "__main__":
    unittest.main()
