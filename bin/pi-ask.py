#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Ask a pi worker one question, in a named session you can ask again.

    pi-ask.py --session review-42 "Review the diff on this branch"
    pi-ask.py --session review-42 "Why do you call finding 3 a bug?"

The same --session resumes the same pi conversation, cache warm, in the
first turn's --dir. The narration goes to ~/.cache/pi-ask/NAME.log; stdout
gets only alerts, then the answer, its cost and the follow-up command. A
worker silent for --idle seconds, or past --max-cost or --max-turns, is
killed, not waited on.
"""

from __future__ import annotations

import argparse
import errno
import fcntl
import importlib.util
import json
import os
import re
import select
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

TOOLBOX_BIN = Path(__file__).resolve().parent


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, TOOLBOX_BIN / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


narrate = _load("_pi_narrate", "pi-narrate.py")
preflight = _load("_preflight", "deepseek-preflight.py")

LOG_DIR = Path.home() / ".cache" / "pi-ask"
KEEP_LOGS_DAYS = 30
# Streaming deltas: most of the log, needed by nothing.
UNLOGGED = {"message_update", "tool_execution_update"}


WORKER_ROLE = (
    "You are a headless worker another agent started with pi-ask.py. Nobody can answer a question, "
    "so never ask one: make a reasonable assumption and say so. Do what the task asks and no more, "
    "and stay in the working directory unless the task names other paths. Your last message is the "
    "whole answer the caller reads: complete and concise, with no preamble."
)
# Both fail at once with no UI.
HEADLESS_EXCLUDED_TOOLS = "ask_user_question,plan_mode_*"

# pi's own rule for session ids.
SESSION_NAME = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?")


def failure(message: dict) -> str | None:
    """Why an assistant message failed, or None."""
    reason = message.get("stopReason")
    if reason == "length":
        return "the reply hit the output token limit and was cut off"
    if reason in ("error", "aborted"):
        return message.get("errorMessage") or reason
    return None


class Alerts:
    """Stdout's share of the narration: alerts, less the known-harmless ones."""

    def __init__(self, first_turn: bool) -> None:
        self.harmless = ['No models match pattern "deepseek/*"', " ■ done — "]
        if first_turn:
            self.harmless.append("No project session found with id")

    def write(self, line: str) -> None:
        if not any(h in line for h in self.harmless):
            sys.stdout.write(line)

    def flush(self) -> None:
        sys.stdout.flush()


class Tally:
    """The run's answer, cost and turns, from pi's events as they arrive."""

    def __init__(self) -> None:
        self.text, self.error = "", None
        self.cost = self.gateway_cost = 0.0
        self.turns = 0

    def feed(self, event: dict) -> None:
        if event.get("type") == "turn_start":
            self.turns += 1
        message = event.get("message")
        if event.get("type") != "message_end" or not isinstance(message, dict) or message.get("role") != "assistant":
            return
        usage = message.get("usage") or {}
        when = datetime.fromtimestamp(message.get("timestamp", time.time() * 1000) / 1000, timezone.utc)
        self.cost += preflight.turn_cost(message.get("model"), usage, when)
        # pi prices it from models.json, as the gateway does.
        self.gateway_cost += float((usage.get("cost") or {}).get("total") or 0)
        parts = [b.get("text", "") for b in message.get("content", []) if b.get("type") == "text"]
        if any(parts):
            self.text = "".join(parts)
        self.error = failure(message)
        if self.error and not any(parts):
            self.text = ""  # earlier filler is not the answer


def pump(proc: subprocess.Popen, log: Path, narrator, tally: Tally, args) -> str | None:
    """Log, tally and narrate pi's output until it ends. Returns why it was cut short, if it was."""
    fd = proc.stdout.fileno()
    pending = b""
    last = time.monotonic()
    with log.open("ab") as raw:
        if raw.tell():
            with log.open("rb") as f:
                f.seek(-1, os.SEEK_END)
                if f.read() != b"\n":  # a killed run's partial line
                    raw.write(b"\n")

        def handle(line: bytes) -> str | None:
            try:
                event = json.loads(line)
            except ValueError:
                event = None
            if not isinstance(event, dict) or event.get("type") not in UNLOGGED:
                raw.write(line + b"\n")
                raw.flush()
            if isinstance(event, dict):
                tally.feed(event)
            narrator.feed(line.decode("utf-8", errors="replace"))
            if tally.cost > args.max_cost:
                return f"spent ${tally.cost:.4f}, over --max-cost ${args.max_cost:g}"
            if tally.turns > args.max_turns:
                return f"over --max-turns {args.max_turns}"
            return None

        while True:
            ready, _, _ = select.select([fd], [], [], 5)
            if not ready:
                if proc.poll() is not None:  # done; a child holds stdout
                    break
                if time.monotonic() - last > args.idle:
                    narrator.emit("!", f"no event for {args.idle}s; killing pi")
                    return "stalled"
                continue
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            last = time.monotonic()
            pending += chunk
            *lines, pending = pending.split(b"\n")
            for line in lines:
                if line.strip() and (over := handle(line)):
                    narrator.emit("!", f"{over}; stopping pi")
                    return over
        if pending.strip():
            handle(pending)
    return None


def prune_logs() -> None:
    """Delete logs and locks untouched for KEEP_LOGS_DAYS. Keep .dir: pi keeps the session."""
    cutoff = time.time() - KEEP_LOGS_DAYS * 86400
    for path in [*LOG_DIR.glob("*.jsonl"), *LOG_DIR.glob("*.log"), *LOG_DIR.glob("*.lock")]:
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            pass


def group_alive(proc: subprocess.Popen) -> bool:
    proc.poll()  # reap pi, or its zombie keeps the group
    try:
        os.killpg(proc.pid, 0)
    except (ProcessLookupError, PermissionError):  # macOS: group already gone
        return False
    return True


def kill_group(proc: subprocess.Popen, grace: float = 10) -> None:
    """End pi and anything it started, such as a server."""
    if not group_alive(proc):
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        return
    # Wait for the group, not just pi: a child may ignore SIGTERM.
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        if not group_alive(proc):
            return
        time.sleep(0.1)
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


class Interrupted(BaseException):
    def __init__(self, signum: int) -> None:
        self.signum = signum


SIGNALS = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)
_caught: int | None = None
_armed = False


def on_signal(signum: int, _frame) -> None:
    """Unwind out of the pump once; outside it, just remember."""
    global _caught, _armed
    _caught = _caught or signum
    if _armed:
        _armed = False
        raise Interrupted(signum)


def main() -> int:
    global _armed
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--session", required=True, help="name; reuse it to follow up")
    p.add_argument("--dir", help="worker cwd; a follow-up reuses the first turn's (default .)")
    p.add_argument("--model", default="cloud", help="LiteLLM alias (default cloud)")
    p.add_argument("--idle", type=int, default=300, help="kill after N silent seconds")
    p.add_argument("--max-cost", type=float, default=0.50, help="stop past $N at DeepSeek's prices (default 0.50)")
    p.add_argument("--max-turns", type=int, default=100, help="stop past N model turns (default 100)")
    p.add_argument("prompt", help="the question, or @file to read it from")
    args = p.parse_args()
    # A worker sees this skill and PATH too.
    if os.environ.get("PI_SUBAGENT_DEPTH", "0") not in ("", "0"):
        print("pi-ask.py: refusing to start a pi worker from inside one (PI_SUBAGENT_DEPTH is set); "
              "do the task yourself", file=sys.stderr)
        return 2
    if not SESSION_NAME.fullmatch(args.session):
        p.error("--session takes letters, digits, '.', '_' and '-', starting and ending alphanumeric")

    prompt = args.prompt
    if prompt.startswith("@"):
        try:
            prompt = Path(prompt[1:]).expanduser().read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            p.error(f"cannot read the prompt file {prompt[1:]}: {e}")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    prune_logs()
    # Two runs at once fork pi's session and mix their logs.
    lock = (LOG_DIR / f"{args.session}.lock").open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(f"pi-ask.py: session {args.session} is already running; wait for it, or use another --session",
              file=sys.stderr)
        return 5
    # pi keys sessions by cwd: another dir silently starts afresh.
    saved = LOG_DIR / f"{args.session}.dir"
    first_turn = not saved.exists()
    workdir = None if first_turn else Path(saved.read_text().strip())
    if args.dir is not None:
        chosen = Path(args.dir).expanduser().resolve()
        if workdir and chosen != workdir:
            p.error(f"session {args.session} runs in {workdir}; leave --dir off, or start a new --session")
        workdir = chosen
    if workdir and not workdir.is_dir():
        p.error(f"--dir {workdir} is not a directory" if args.dir is not None else
                f"session {args.session}'s dir {workdir} is gone; start a new --session")
    workdir = workdir or Path.cwd()
    saved.write_text(f"{workdir}\n")
    log = LOG_DIR / f"{args.session}.jsonl"

    # Depth 1: headless hard-block mode, no git writes.
    env = dict(os.environ, PATH=f"{TOOLBOX_BIN}:{os.environ.get('PATH', '')}", PI_SUBAGENT_DEPTH="1")
    # "--": a prompt may start with - or ---.
    cmd = ["pi", "--mode", "json", "--approve", "--provider", "litellm", "--model", args.model,
           "--session-id", args.session, "--append-system-prompt", WORKER_ROLE,
           "--exclude-tools", HEADLESS_EXCLUDED_TOOLS, "--", prompt]
    # Before Popen, so no signal leaves pi orphaned.
    for sig in SIGNALS:
        signal.signal(sig, on_signal)
    try:
        # DEVNULL: pi reads piped stdin to EOF first.
        proc = subprocess.Popen(cmd, cwd=workdir, env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                start_new_session=True)
    except FileNotFoundError:
        print("pi-ask.py: pi is not on PATH", file=sys.stderr)
        return 2
    except OSError as e:
        if e.errno != errno.E2BIG:
            raise
        print(f"pi-ask.py: the prompt ({len(prompt.encode())} bytes) is over the OS argument limit; shorten it",
              file=sys.stderr)
        return 2
    narration_path = LOG_DIR / f"{args.session}.log"
    narration = narration_path.open("a", encoding="utf-8")
    narrator = narrate.Narrator(label=args.session, out=narration, alerts=Alerts(first_turn))
    print(f"pi-ask: {args.session} running in {workdir}; narration in {narration_path}", flush=True)
    tally = Tally()
    cut_short = None
    try:
        _armed = True
        if _caught:
            raise Interrupted(_caught)
        cut_short = pump(proc, log, narrator, tally, args)
    except Interrupted as e:
        narrator.emit("!", f"{signal.Signals(e.signum).name}; stopping pi")
    finally:
        _armed = False
        # pi has its own group, so pass our death on.
        kill_group(proc)
    code = proc.wait()
    narrator.finish()

    text, error = tally.text, tally.error
    print(f"\n=== answer ({args.session}: ${tally.cost:.4f} at DeepSeek's prices; "
          f"the gateway's daily cap counts ${tally.gateway_cost:.4f}) ===")
    print(text or "(no answer)")
    if error:
        print(f"=== the last turn failed: {error} ===")
    if cut_short and cut_short != "stalled":
        print(f"=== stopped: {cut_short} ===")
    print(f"=== follow up: pi-ask.py --session {args.session} \"...\" (it runs in {workdir}) ===")
    print(f"=== logs: {narration_path} (narration), {log} (pi's events) ===")
    if _caught:
        print(f"=== stopped by {signal.Signals(_caught).name} ===")
        return 128 + _caught
    if cut_short == "stalled":
        return 3
    if cut_short:
        return 4
    if error:
        return code or 1
    return code or (0 if text else 1)


if __name__ == "__main__":
    sys.exit(main())
