"""Per-command and per-turn timing in a worker's log, and run-report.py's split of it."""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from _loader import load

loop = load("overnight-loop.py")
report = load("run-report.py")
steptime = load("steptime.py")
runlog = load("runlog.py")


def turn(ms_start: int, took: int, calls: list[tuple[str, str]]) -> list[dict]:
    """An assistant turn asking for bash calls, then the calls finishing."""
    msg = {"role": "assistant", "timestamp": ms_start, "durationMs": took}
    out: list[dict] = [{"type": "message_end", "message": msg}]
    for i, (cmd, _) in enumerate(calls):
        out.append({"type": "tool_execution_start", "toolCallId": f"c{ms_start}{i}", "toolName": "bash",
                    "args": {"command": cmd}})
    for i, (_, spec) in enumerate(calls):
        secs, code = spec.split(":")
        out.append({"type": "tool_execution_end", "toolCallId": f"c{ms_start}{i}", "toolName": "bash",
                    "result": {"content": [], "exit_code": int(code)}, "durationMs": int(secs) * 1000,
                    "isError": False})
    return out


STREAM = "\n".join(
    ["Warning: new session", "not json"]
    + [json.dumps(e) for e in turn(1_000_000, 4000, [("uv run pytest -q", "30:0")])]
    + [json.dumps(e) for e in turn(1_100_000, 6000, [("./verify.sh | tail", "100:1"), ("ls", "1:0")])]
    + [json.dumps(e) for e in turn(1_300_000, 2000, [("python3 sweep.py --n 9", "50:0")])]
) + "\n"


class StepsTest(unittest.TestCase):
    def test_commands_carry_duration_exit_and_category(self) -> None:
        cmds = [s for s in steptime.steps(STREAM) if s["step"] == "cmd"]
        got = [(s["cmd"], s["seconds"], s["exit"], s["cat"]) for s in cmds]
        self.assertEqual(got, [("uv run pytest -q", 30.0, 0, "test runs"), ("./verify.sh | tail", 100.0, 1, "gates"),
                               ("ls", 1.0, 0, "other commands"), ("python3 sweep.py --n 9", 50.0, 0, "sweeps")])

    def test_each_llm_turn_is_timed(self) -> None:
        got = [s["seconds"] for s in steptime.steps(STREAM) if s["step"] == "llm"]
        self.assertEqual(got, [4.0, 6.0, 2.0])

    def test_a_command_starts_when_its_turn_ends(self) -> None:
        first = next(s for s in steptime.steps(STREAM) if s["step"] == "cmd")
        self.assertEqual(first["t"], 1004.0)


class LoopLogTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        saved = {k: os.environ.pop(k) for k in list(os.environ) if k.startswith("RUN_LOG_")}
        self.addCleanup(os.environ.update, saved)
        os.environ["RUN_LOG_DIR"] = str(self.root / "logs")
        os.environ["RUN_LOG_TICKET"] = "7"
        runlog.start("r1")

    def test_the_issue_log_and_run_log_get_one_line_per_step(self) -> None:
        log = self.root / "7.log"
        loop.log_steps(STREAM, log)
        lines = [json.loads(x) for x in log.read_text().splitlines()]
        self.assertEqual([x["step"] for x in lines].count("cmd"), 4)
        self.assertEqual([x["step"] for x in lines].count("llm"), 3)
        events = [json.loads(x) for x in runlog.log_path("r1").read_text().splitlines()]
        kinds = [e["kind"] for e in events]
        self.assertEqual((kinds.count("worker_cmd"), kinds.count("llm_turn")), (4, 3), kinds)
        gate = next(e for e in events if e["kind"] == "worker_cmd" and e["cat"] == "gates")
        self.assertEqual((gate["seconds"], gate["exit"], gate["ticket"]), (100.0, 1, "7"))

    def test_a_stream_without_steps_adds_nothing(self) -> None:
        log = self.root / "7.log"
        loop.log_steps("no pi events here\n", log)
        self.assertFalse(log.exists())

    def test_step_lines_in_a_log_read_back_unchanged(self) -> None:
        log = self.root / "7.log"
        loop.log_steps(STREAM, log)
        self.assertEqual(steptime.steps(log.read_text()), steptime.steps(STREAM))


class ReportSplitTest(unittest.TestCase):
    def events(self) -> list[dict]:
        return [{"t": 1.0, "kind": e["kind"], "lane": "a", "ticket": "7", **e} for e in [
            {"kind": "llm_turn", "seconds": 100},
            {"kind": "worker_cmd", "seconds": 300, "cat": "test runs", "cmd": "pytest"},
            {"kind": "worker_cmd", "seconds": 400, "cat": "gates", "cmd": "./verify.sh"},
            {"kind": "worker_cmd", "seconds": 150, "cat": "sweeps", "cmd": "sweep.py"},
            {"kind": "worker_cmd", "seconds": 50, "cat": "other commands", "cmd": "git log"},
            *({"kind": "worker_cmd", "seconds": 1, "cat": "other commands", "cmd": f"ls {i}"} for i in range(4)),
        ]]

    def test_a_ticket_splits_by_category_with_its_top_five_commands(self) -> None:
        out = report.worker_block(report.worker_steps(self.events()))
        row = next(line for line in out.splitlines() if line.startswith("#7"))
        for want in ("LLM thinking", "10%", "30%", "40%", "15%", "5%"):
            self.assertIn(want, out + row)
        self.assertIn("17m", row)
        tops = out.split("top commands, #7:")[1].strip().splitlines()
        self.assertEqual(len(tops), 5, tops)
        self.assertIn("verify.sh", tops[0])

    def test_a_log_of_an_older_loop_still_splits(self) -> None:
        path = Path(tempfile.mkdtemp()) / "7.log"
        path.write_text(STREAM)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(report.main(["--log", str(path)]), 0)
        self.assertIn("verify.sh", out.getvalue())
        self.assertIn("test runs", out.getvalue())

    def test_a_run_without_steps_prints_no_worker_block(self) -> None:
        self.assertEqual(report.worker_block(report.worker_steps([])), "")


class HungTest(unittest.TestCase):
    STREAM = "\n".join(json.dumps(e) for e in [
        {"type": "message_end", "message": {"role": "assistant", "timestamp": 1_000_000, "durationMs": 1000}},
        {"type": "tool_execution_start", "toolCallId": "h", "toolName": "bash", "args": {"command": "godot --headless"}},
        {"type": "tool_execution_end", "toolCallId": "h", "toolName": "bash", "isError": True, "durationMs": 2_400_000,
         "result": {"content": [{"type": "text", "text": "Command timed out after 2400 seconds"}]}},
        {"type": "tool_execution_start", "toolCallId": "f", "toolName": "bash", "args": {"command": "false"}},
        {"type": "tool_execution_end", "toolCallId": "f", "toolName": "bash", "isError": True, "durationMs": 1000,
         "result": {"content": [{"type": "text", "text": "nope"}]}},
    ])

    def test_only_a_tool_timeout_is_hung(self) -> None:
        cmds = [s for s in steptime.steps(self.STREAM) if s["step"] == "cmd"]
        self.assertEqual([bool(s.get("hung")) for s in cmds], [True, False], f"got {cmds}")

    def test_the_report_names_the_hung_command_in_both_blocks(self) -> None:
        by_ticket = report.worker_steps(report.log_events_text(self.STREAM, "7"))
        self.assertIn("hung: 'godot --headless' 40m (#7)", report.worker_block(by_ticket))
        rows = {"7": {"spent": {p: 0 for p in report.PHASES}, "dup_s": 0}}
        ranked = report.ranked_waits(rows, hung=report.hung_lines(by_ticket))
        self.assertIn("hung", ranked)
        self.assertIn("40", ranked)


class MissingRunTest(unittest.TestCase):
    def test_a_missing_log_names_the_run_the_events_went_to(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            saved = os.environ.get("RUN_LOG_DIR")
            os.environ["RUN_LOG_DIR"] = tmp
            try:
                runlog.start("older-run")
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    self.assertEqual(report.main(["never-started"]), 1)
            finally:
                os.environ.pop("RUN_LOG_DIR") if saved is None else os.environ.update(RUN_LOG_DIR=saved)
        self.assertIn("current run is 'older-run'", err.getvalue())
        self.assertIn("runlog.py start never-started", err.getvalue())


if __name__ == "__main__":
    unittest.main()
