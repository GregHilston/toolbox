"""The commander's shift tools: log-order.py, shift-arm --log, commander-roll and control-loop.sh."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_claude_shift import (  # noqa: E402
    PANE, ROOT, Base, claude_shift, roll, script,
)  # fmt: skip

HOOK = ROOT / "dot/claude/.claude/hooks/log-order.py"
LOOP_HC = """#!/bin/sh
echo "$*" >> "$CALLS"
case "$1" in
get) printf '{"state":"live","status":{"app":"claude-code","state":"%s"}}\\n' "$(cat "$STATUS")" ;;
send)
  if [ -e "$DROP" ] && [ ! -e "$DROP.used" ]; then : > "$DROP.used"; exit 0; fi
  echo "$3" >> "$SENT"; cp "$SENT" "$SCREEN" ;;
read) cat "$SCREEN" ;;
esac
"""
LOG_TEXT = "# Run\n\n## Current\n\norders: none\n\n## Journal\n\n### 2026-11-20 08:00 Greg\n\nstart\n\n### 2026-11-20 08:01 started\n\nok\n"


class Commander(Base):
    def setUp(self) -> None:
        super().setUp()
        self.repo = self.tmp / "repo"
        self.origin = self.tmp / "origin.git"
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
        self.git = lambda *a, cwd=self.repo: subprocess.run([*git, *a], cwd=cwd, capture_output=True, text=True, check=True)
        subprocess.run(["git", "init", "-q", "--bare", self.origin], check=True)
        self.repo.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("remote", "add", "origin", str(self.origin))
        self.logfile = self.repo / "run.md"
        self.logfile.write_text(LOG_TEXT)
        self.git("add", "run.md")
        self.git("commit", "-q", "-m", "init")
        self.git("push", "-q", "-u", "origin", "main")
        self.stub = script(self.tmp / "orch-roll", '#!/bin/sh\necho "$*" >> "$CALLS"\necho queued\nexit ${STUB_EXIT:-0}\n')
        self.env |= {
            "ORCHESTRATOR_ROLL": self.stub, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
        }  # fmt: skip

    def cr(self, **env: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, ROOT / "bin/commander-roll"], capture_output=True, text=True, env=self.env | env)


class OrderHook(Commander):
    def submit(self, prompt: str, env: dict | None = None) -> None:
        out = subprocess.run([sys.executable, HOOK], input=json.dumps({"prompt": prompt}), capture_output=True, text=True, env=env or self.env)
        self.assertEqual((out.returncode, out.stdout), (0, ""))

    def test_orders_are_appended_with_their_author(self) -> None:
        self.arm(log=str(self.logfile))
        self.submit("keep going")
        self.submit("XO: loser-picks: blocked")
        text = self.logfile.read_text()
        self.assertTrue(text.startswith(LOG_TEXT))
        headings = [ln.split()[-1] for ln in text.splitlines() if ln.startswith("### ")][2:]
        self.assertEqual(headings, ["Greg", "XO"])
        self.assertIn("\nkeep going\n", text)
        self.assertIn("\nXO: loser-picks: blocked\n", text)

    def test_relays_and_notifications_are_notices(self) -> None:
        self.arm(log=str(self.logfile))
        for p in ("<task-notification>\n<summary>done</summary>", '<hc from="moriats/t21">CAG: parked</hc>', "<agent-message from=\"a\">x"):
            self.submit(p)
        headings = [ln.split()[-1] for ln in self.logfile.read_text().splitlines() if ln.startswith("### ")][2:]
        self.assertEqual(headings, ["notice"] * 3)

    def test_the_restart_prompt_is_not_an_order(self) -> None:
        self.arm(log=str(self.logfile), prompt="Fresh shift.")
        self.submit("Fresh shift.")
        self.assertIn(" restart\n", self.logfile.read_text())

    def test_unarmed_or_logless_panes_write_nothing(self) -> None:
        self.submit("hello")
        self.arm()
        self.submit("hello")
        self.submit("hello", env=self.env | {"HERDR_PANE_ID": ""})
        self.assertEqual(self.logfile.read_text(), LOG_TEXT)

    def test_a_broken_log_path_never_blocks(self) -> None:
        self.arm(log=str(self.tmp / "no/such/dir/run.md"))
        self.submit("hello")


class DrainText(Commander):
    def test_a_logged_commander_is_told_commander_roll(self) -> None:
        self.arm(log=str(self.logfile), drain="Rewrite Current.")
        self.transcript.write_text(json.dumps({"type": "assistant", "message": {"model": "m", "usage": {"input_tokens": 9000}}}) + "\n")
        event = {"session_id": "s", "transcript_path": str(self.transcript), "stop_hook_active": False, "background_tasks": [], "session_crons": []}
        out = subprocess.run([sys.executable, ROOT / "dot/claude/.claude/hooks/shift-drain.py"], input=json.dumps(event), capture_output=True, text=True, env=self.env)
        reason = json.loads(out.stdout)["reason"]
        self.assertIn("`commander-roll`", reason)
        self.assertNotIn("orchestrator-roll", reason)


class ArmLog(Commander):
    def test_log_is_kept_on_rearm(self) -> None:
        config = self.tmp / "claude"
        (config / "hooks").mkdir(parents=True)
        hook = config / "hooks/shift-drain.py"
        hook.write_text("#!/bin/sh\n")
        hook.chmod(0o755)
        (config / "settings.json").write_text(json.dumps({"hooks": {"Stop": [{"hooks": [{"command": str(hook)}]}]}}))
        env = self.env | {"CLAUDE_CONFIG_DIR": str(config)}
        arm = lambda *a: subprocess.run([sys.executable, ROOT / "bin/shift-arm", "--prompt", "go", *a], capture_output=True, text=True, env=env)
        self.assertEqual(arm("--log", str(self.logfile)).returncode, 0)
        claude_shift.save(PANE, self.state() | {"log_hash": "abc"})
        self.assertEqual(arm().returncode, 0)
        state = self.state()
        self.assertEqual((state["log"], state["log_hash"]), (str(self.logfile), "abc"))


class CommanderRoll(Commander):
    def test_refuses_without_a_log_key(self) -> None:
        self.arm(repo=str(self.repo))
        out = self.cr()
        self.assertEqual(out.returncode, 1)
        self.assertIn("--log", out.stderr)
        self.assertEqual(self.calls.read_text(), "")

    def test_rolls_when_current_changed_then_refuses_when_not(self) -> None:
        self.arm(repo=str(self.repo), log=str(self.logfile))
        self.logfile.write_text(LOG_TEXT.replace("orders: none", "orders: hold B"))
        out = self.cr()
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("queued", out.stdout)
        self.assertEqual(self.git("log", "-1", "--format=%s%n%b").stdout.count("Claude"), 0)
        self.assertEqual(self.git("diff", "origin/main", "--stat", "--", "run.md").stdout, "")
        pending = self.state()["roll_hash"]
        # the worker records it once the restart prompt is in
        self.queue_worker()
        self.assertEqual(self.state()["log_hash"], pending)
        again = self.cr()
        self.assertEqual(again.returncode, 1)
        self.assertIn("## Current", again.stderr)

    def queue_worker(self) -> None:
        claude_shift.save(PANE, self.state() | {"roll_id": "t0k", "roll_stops": 1, "stops": 2, "announced": "s1", "tokens": 5000})
        roll.worker(PANE, "t0k")

    def test_a_failed_roll_can_be_retried(self) -> None:
        self.arm(repo=str(self.repo), log=str(self.logfile))
        self.logfile.write_text(LOG_TEXT.replace("orders: none", "orders: x"))
        self.assertEqual(self.cr(STUB_EXIT="1").returncode, 1)
        self.assertNotIn("log_hash", self.state())
        self.assertEqual(self.cr().returncode, 0)

    def test_only_the_log_is_committed(self) -> None:
        self.arm(repo=str(self.repo), log=str(self.logfile))
        (self.repo / "other.txt").write_text("x")
        self.git("add", "other.txt")
        self.logfile.write_text(LOG_TEXT.replace("orders: none", "orders: y"))
        self.assertEqual(self.cr().returncode, 0)
        self.assertEqual(self.git("show", "--name-only", "--format=", "HEAD").stdout.split(), ["run.md"])

    def test_push_failure_is_printed_and_the_roll_goes_on(self) -> None:
        self.git("remote", "set-url", "origin", str(self.tmp / "gone.git"))
        self.arm(repo=str(self.repo), log=str(self.logfile))
        self.logfile.write_text(LOG_TEXT.replace("orders: none", "orders: z"))
        out = self.cr()
        self.assertEqual(out.returncode, 0)
        self.assertIn("push failed", out.stderr + out.stdout)
        self.assertIn("queued", out.stdout)

    def test_refuses_while_gregs_last_message_is_unanswered(self) -> None:
        self.arm(repo=str(self.repo), log=str(self.logfile))
        asked = LOG_TEXT.replace("orders: none", "orders: q") + "\n### 2026-11-20 09:00 Greg\n\nwhat about X?\n\n### 2026-11-20 09:01 XO\n\nXO: idle\n"
        self.logfile.write_text(asked)
        out = self.cr()
        self.assertEqual(out.returncode, 1)
        self.assertIn("09:00", out.stderr)
        self.assertEqual(self.calls.read_text(), "")
        self.logfile.write_text(asked + "\n### 2026-11-20 09:02 X answered\n\nanswered\n")
        self.assertEqual(self.cr().returncode, 0)

    def test_missing_current_section_refuses(self) -> None:
        self.arm(repo=str(self.repo), log=str(self.logfile))
        self.logfile.write_text("# Run\n\n## Journal\n")
        self.assertEqual(self.cr().returncode, 1)


class ControlLoop(Base):
    LOOP = ROOT / "bin/control-loop.sh"

    def setUp(self) -> None:
        super().setUp()
        self.bin = self.tmp / "fakebin"
        self.bin.mkdir()
        script(self.bin / "ssh", '#!/bin/sh\ncat "$SSH_OUT"\n')
        script(self.bin / "gh", '#!/bin/sh\nexit 0\n')
        script(self.bin / "hc", LOOP_HC)
        self.out, self.sent, self.screen = self.tmp / "ssh-out", self.tmp / "sent", self.tmp / "screen"
        for f in (self.sent, self.screen):
            f.touch()
        self.out.write_text("MAIN abc\n")
        self.cl = self.tmp / "cl"
        self.env |= {
            "PATH": f"{self.bin}:{os.environ['PATH']}", "CONTROL_LOOP_DIR": str(self.cl), "SSH_OUT": str(self.out),
            "SENT": str(self.sent), "SCREEN": str(self.screen), "DROP": str(self.tmp / "drop"),
            "CL_POLL": "0.05", "CL_SETTLE": "0", "CL_IDLE_TIMEOUT": "0.3", "CL_ROLL_TIMEOUT": "0.3", "HC_BIN_PATH": str(self.bin / "hc"),
        }  # fmt: skip

    def loop(self, *args: str, **env: str) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", self.LOOP, *args], capture_output=True, text=True, env=self.env | env, timeout=30)

    def test_once_prints_alerts_and_wakes_nobody(self) -> None:
        self.out.write_text("XO loser-picks: blocked: pick a model\nMAIN abc\n")
        out = self.loop("--once", "--wake", "hc:t3")
        self.assertIn("XO loser-picks: blocked: pick a model", out.stdout)
        self.assertEqual(self.sent.read_text(), "")

    def test_once_quiet_prints_nothing_and_beats(self) -> None:
        out = self.loop("--once")
        self.assertEqual((out.returncode, out.stdout.strip()), (0, ""))
        self.assertTrue((self.cl / "loser-picks/heartbeat").exists())

    def test_watch_file_names_the_tickets(self) -> None:
        script(self.bin / "gh", '#!/bin/sh\ncase "$*" in *"issue view 355"*) echo CLOSED ;; *"issue view 400"*) echo OPEN ;; esac\n')
        (self.cl / "loser-picks").mkdir(parents=True)
        (self.cl / "loser-picks/closes").write_text("355\n400\n")
        out = self.loop("--once").stdout
        self.assertIn("#355 closed", out)
        self.assertNotIn("#400", out)

    def test_nothing_landed_clock_survives_a_restart(self) -> None:
        (self.cl / "loser-picks").mkdir(parents=True)
        (self.cl / "loser-picks/main").write_text("abc 1000\n")
        self.assertIn("nothing landed on origin/main for", self.loop("--once").stdout)
        (self.cl / "loser-picks/main").write_text("zzz 1000\n")  # a new sha resets it
        self.assertNotIn("nothing landed", self.loop("--once").stdout)

    def test_a_second_loop_on_the_same_target_refuses(self) -> None:
        holder = subprocess.Popen(["bash", self.LOOP, "--wake", "hc:t3", "3600"], env=self.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(holder.kill)
        for _ in range(100):
            if (self.cl / "loser-picks/heartbeat").exists():
                break
            subprocess.run(["sleep", "0.1"])
        out = self.loop("--wake", "hc:t3")
        self.assertEqual(out.returncode, 1)
        self.assertIn(str(holder.pid), out.stderr)

    def test_send_types_into_the_pane_and_reads_it_back(self) -> None:
        self.assertEqual(self.loop("--wake", "hc:t3", "--send", "XO: hello there").returncode, 0)
        self.assertEqual(self.sent.read_text().splitlines(), ["XO: hello there"])

    def test_send_resends_once_when_the_text_vanished(self) -> None:
        (self.tmp / "drop").touch()
        self.assertEqual(self.loop("--wake", "hc:t3", "--send", "XO: hello there").returncode, 0)
        self.assertEqual(self.sent.read_text().splitlines(), ["XO: hello there"])
        self.assertEqual(self.calls.read_text().count("send t3"), 2)

    def test_send_waits_while_the_target_works_then_sends_anyway(self) -> None:
        self.status.write_text("working")
        self.assertEqual(self.loop("--wake", "hc:t3", "--send", "XO: hi").returncode, 0)
        self.assertEqual(self.sent.read_text().splitlines(), ["XO: hi"])

    def test_send_holds_while_a_roll_is_queued(self) -> None:
        claude_shift.save("hc:t3", {**self.base("hc:t3"), "roll_id": "r1", "worker_pid": 1})

        def clear() -> None:
            time.sleep(0.15)
            claude_shift.save("hc:t3", self.base("hc:t3"))
        t = threading.Thread(target=clear)
        t.start()
        out = self.loop("--wake", "hc:t3", "--send", "XO: later", CL_ROLL_TIMEOUT="5")
        t.join()
        self.assertEqual(out.returncode, 0)
        self.assertEqual(self.sent.read_text().splitlines(), ["XO: later"])

    def base(self, pane: str) -> dict:
        return {"pane": pane, "threshold": 1000, "prompt": "go", "max_rolls": 2, "rolls": 0, "repo": "/r", **claude_shift.RUNTIME}


if __name__ == "__main__":
    unittest.main()
