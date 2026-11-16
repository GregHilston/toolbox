"""The shift tools: shift-drain.py, claude_shift.py and orchestrator-roll, against stand-in herdr and pushover."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "dot/claude/.claude/hooks/shift-drain.py"
sys.path.insert(0, str(ROOT / "bin"))
import claude_shift  # noqa: E402

# Extensionless, so _loader's spec lookup can't see it.
_loader = importlib.machinery.SourceFileLoader("_orchestrator_roll", str(ROOT / "bin/orchestrator-roll"))
roll = importlib.util.module_from_spec(importlib.util.spec_from_loader(_loader.name, _loader))
_loader.exec_module(roll)

FAKE_HERDR = """#!/bin/sh
echo "$*" >> "$CALLS"
case "$1 $2" in
"agent get") printf '{"result":{"agent":{"agent_status":"%s"}}}\\n' "$(cat "$STATUS")" ;;
"agent prompt")
  case "$*" in
  *--wait*)
    [ -n "$PROMPT_BODY" ] && { echo "$PROMPT_BODY"; exit 0; } ;;
  esac
  echo '{"result":{"type":"ok"}}' ;;
esac
"""
FAKE_PUSHOVER = """#!/bin/sh
echo "$2" >> "$PUSHES"
echo '<Response [200]>'
"""
PANE = "w1:p1"
TOKEN = "t0k"


def assistant(tokens: int, **extra) -> dict:
    usage = {"input_tokens": 1, "cache_read_input_tokens": tokens - 1, "cache_creation_input_tokens": 0}
    return {"type": "assistant", "message": {"model": "claude-x", "usage": usage}, **extra}


def script(path: Path, body: str) -> str:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)


class Base(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.transcript = self.tmp / "t.jsonl"
        self.calls, self.pushes, self.status = self.tmp / "calls", self.tmp / "pushes", self.tmp / "status"
        for f in (self.calls, self.pushes):
            f.touch()
        self.status.write_text("idle")
        pushover = script(self.tmp / "pushover", FAKE_PUSHOVER)
        self.env = os.environ | {
            "CLAUDE_SHIFT_DIR": str(self.tmp), "HERDR_PANE_ID": PANE, "PUSHOVER_BIN": pushover, "TOOLBOX_HOME": str(ROOT),
            "CALLS": str(self.calls), "PUSHES": str(self.pushes), "STATUS": str(self.status),
        }  # fmt: skip
        self.patch(claude_shift, "STATE_DIR", self.tmp)
        self.patch(claude_shift, "PUSHOVER", pushover)
        for key in ("CALLS", "PUSHES", "STATUS"):
            self.patch(os.environ, key, self.env[key], item=True)
        self.patch(roll, "HERDR", script(self.tmp / "herdr", FAKE_HERDR))
        for name, value in (("SETTLE", 0), ("POLL", 0.01), ("DRAIN_TIMEOUT", 0.3), ("CLEAR_TIMEOUT", 0.3)):
            self.patch(roll, name, value)

    def patch(self, obj, name, value, item=False) -> None:
        if item:
            old = obj.get(name)
            obj[name] = value
            self.addCleanup(lambda: obj.pop(name) if old is None else obj.__setitem__(name, old))
            return
        old = getattr(obj, name)
        setattr(obj, name, value)
        self.addCleanup(setattr, obj, name, old)

    def arm(self, **state) -> None:
        base = {"pane": PANE, "threshold": 1000, "prompt": "go", "max_rolls": 2, "rolls": 0, "repo": "/r", **claude_shift.RUNTIME}
        claude_shift.save(PANE, base | state)

    def state(self) -> dict:
        return claude_shift.load(PANE)

    def write(self, *entries: dict) -> None:
        self.transcript.write_text("".join(json.dumps(e) + "\n" for e in entries))


class Hook(Base):
    def stop(self, session: str = "s1", active: bool = False, env: dict | None = None, **extra) -> dict | None:
        event = {"session_id": session, "transcript_path": str(self.transcript), "stop_hook_active": active,
                 "background_tasks": [], "session_crons": []} | extra  # fmt: skip
        out = subprocess.run([sys.executable, HOOK], input=json.dumps(event), capture_output=True, text=True, env=env or self.env)
        self.assertEqual(out.returncode, 0)
        return json.loads(out.stdout) if out.stdout.strip() else None

    def test_tokens_skip_sidechain_and_synthetic(self) -> None:
        synthetic = assistant(9)
        synthetic["message"]["model"] = "<synthetic>"
        self.write(assistant(500), {"type": "user"}, assistant(7, isSidechain=True), synthetic)
        self.assertEqual(claude_shift.context_tokens(self.transcript), 500)

    def test_tokens_found_beyond_first_chunk(self) -> None:
        self.write(assistant(1234), *[{"type": "user", "pad": "x" * 1000}] * 300)
        self.assertEqual(claude_shift.context_tokens(self.transcript), 1234)

    def test_unarmed_never_blocks_or_writes(self) -> None:
        self.write(assistant(10**6))
        self.assertIsNone(self.stop())
        self.assertIsNone(self.stop(env=self.env | {"HERDR_PANE_ID": ""}))
        self.assertEqual(list(self.tmp.glob("*.json")), [])

    def test_blocks_once_per_session_and_again_after_a_roll(self) -> None:
        self.arm()
        self.write(assistant(999))
        self.assertIsNone(self.stop())
        self.write(assistant(5000))
        self.assertEqual(self.stop()["decision"], "block")
        self.assertIsNone(self.stop())
        self.assertIsNone(self.stop("s2", active=True))
        self.assertIn("orchestrator-roll", self.stop("s2")["reason"])
        state = self.state()
        claude_shift.save(PANE, state | {"announced": None})  # the worker after /clear
        self.assertIsNotNone(self.stop("s2"))
        self.assertEqual(self.state()["stops"], 6)

    def test_records_live_work(self) -> None:
        self.arm()
        self.write(assistant(5))
        self.stop(background_tasks=[{"id": "a"}], session_crons=[{"id": "c"}])
        self.assertEqual(self.state()["busy"], 2)
        self.stop(background_tasks=None)
        self.assertEqual(self.state()["busy"], -1)

    def test_spent_rolls_say_stop(self) -> None:
        self.arm(rolls=2)
        self.write(assistant(5000))
        self.assertIn("will refuse", self.stop()["reason"])

    def test_corrupt_state_is_moved_aside_and_pushed(self) -> None:
        claude_shift.state_path(PANE).write_text('{"pane": "w1:p1"}')
        self.write(assistant(5000))
        self.assertIsNone(self.stop())
        self.assertTrue(claude_shift.state_path(PANE).with_suffix(".bad").exists())
        for _ in range(50):
            if self.pushes.read_text():
                break
            time.sleep(0.05)
        self.assertIn("corrupt", self.pushes.read_text())


class Worker(Base):
    def queue(self, **state) -> None:
        self.arm(**{"roll_id": TOKEN, "roll_stops": 1, "stops": 2, "announced": "s1", "tokens": 5000} | state)

    def run_worker(self) -> list[str]:
        roll.worker(PANE, TOKEN)
        return self.calls.read_text().splitlines()

    def test_roll_counts_only_after_the_prompt_is_in(self) -> None:
        self.queue()
        calls = self.run_worker()
        prompts = [c for c in calls if c.startswith("agent prompt")]
        self.assertEqual(prompts[0], f"agent prompt {PANE} /clear")
        self.assertTrue(prompts[1].startswith(f"agent prompt {PANE} go --wait"))
        state = self.state()
        self.assertEqual((state["rolls"], state["roll_id"], state["announced"]), (1, None, None))
        self.assertIn("rolled shift 1/2 at 5k tokens", self.pushes.read_text())

    def test_wait_timeout_body_is_only_a_warning(self) -> None:
        self.patch(os.environ, "PROMPT_BODY", '{"error":{"code":"timeout","message":"timed out"}}', item=True)
        self.queue()
        self.run_worker()
        self.assertEqual(self.state()["rolls"], 1)

    def test_error_body_on_exit_0_fails_and_reopens_the_drain(self) -> None:
        self.patch(os.environ, "PROMPT_BODY", '{"error":{"code":"agent_blocked","message":"dialog"}}', item=True)
        self.queue()
        self.run_worker()
        state = self.state()
        self.assertEqual((state["rolls"], state["roll_id"], state["announced"]), (0, None, None))
        self.assertIn("failed while sending the restart prompt", self.pushes.read_text())

    def test_live_work_holds_the_clear(self) -> None:
        self.queue(busy=1)
        calls = self.run_worker()
        self.assertFalse(any("/clear" in c for c in calls))
        self.assertIsNone(self.state()["announced"])
        self.assertIn("failed while waiting", self.pushes.read_text())

    def test_no_stop_since_the_roll_holds_the_clear(self) -> None:
        self.queue(stops=1)
        self.assertFalse(any("/clear" in c for c in self.run_worker()))

    def test_off_cancels_a_queued_roll(self) -> None:
        self.queue()
        claude_shift.state_path(PANE).unlink()
        self.assertFalse(any("prompt" in c for c in self.run_worker()))
        self.assertEqual(self.pushes.read_text(), "")


class Cli(Base):
    def run_roll(self, *args: str) -> subprocess.CompletedProcess:
        env = self.env | {"HERDR_BIN_PATH": roll.HERDR}
        return subprocess.run([sys.executable, ROOT / "bin/orchestrator-roll", *args], capture_output=True, text=True, env=env)

    def test_refusals_exit_1(self) -> None:
        self.assertEqual(self.run_roll().returncode, 1)  # unarmed
        self.arm(rolls=2)
        self.assertIn("2/2 rolls used", self.run_roll().stderr)
        claude_shift.state_path(PANE).write_text("{")
        self.assertIn("corrupt", self.run_roll().stderr)

    def test_no_stop_ever_counted_refuses(self) -> None:
        self.arm(stops=0)
        out = self.run_roll()
        self.assertEqual(out.returncode, 1)
        self.assertIn("Stop hook has never run", out.stderr)

    def test_a_counted_stop_passes_the_hook_check(self) -> None:
        self.arm(stops=1)
        self.assertNotIn("never run", self.run_roll().stderr)

    def test_unknown_argument_exits_2(self) -> None:
        self.assertEqual(self.run_roll("--bogus").returncode, 2)


class ArmCli(Base):
    def setUp(self) -> None:
        super().setUp()
        self.config = self.tmp / "claude"
        (self.config / "hooks").mkdir(parents=True)
        self.env |= {"CLAUDE_CONFIG_DIR": str(self.config)}

    def install(self, executable: bool = True, listed: bool = True) -> None:
        hook = self.config / "hooks/shift-drain.py"
        hook.write_text("#!/bin/sh\n")
        hook.chmod(0o755 if executable else 0o644)
        command = str(hook) if listed else "other.py"
        settings = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": command}]}]}}
        (self.config / "settings.json").write_text(json.dumps(settings))

    def arm_cli(self) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, ROOT / "bin/shift-arm", "--prompt", "go"], capture_output=True, text=True, env=self.env)

    def test_missing_hook_file_refuses_to_arm(self) -> None:
        out = self.arm_cli()
        self.assertEqual(out.returncode, 1)
        self.assertIn("shift-drain.py is missing", out.stderr)
        self.assertIsNone(claude_shift.load(PANE))

    def test_hook_not_executable_refuses(self) -> None:
        self.install(executable=False)
        self.assertEqual(self.arm_cli().returncode, 1)

    def test_hook_not_in_settings_refuses(self) -> None:
        self.install(listed=False)
        out = self.arm_cli()
        self.assertEqual(out.returncode, 1)
        self.assertIn("names shift-drain.py", out.stderr)
        self.assertIsNone(claude_shift.load(PANE))

    def test_installed_hook_arms(self) -> None:
        self.install()
        out = self.arm_cli()
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIsNotNone(claude_shift.load(PANE))


if __name__ == "__main__":
    unittest.main()
