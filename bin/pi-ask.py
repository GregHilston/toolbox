#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Ask a pi worker one question, in a named session you can ask again.

    pi-ask.py --session review-42 "Review the diff on this branch"
    pi-ask.py --session review-42 "Why do you call finding 3 a bug?"

The same --session resumes the same pi conversation, cache warm. Progress
streams one line per event; the answer, its cost and the log path print
at the end. A worker silent for --idle seconds is killed, not waited on.
"""

from __future__ import annotations

import argparse
import errno
import importlib.util
import json
import os
import re
import select
import shlex
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


def answer_and_cost(log: Path, since: int) -> tuple[str, float, str | None]:
    """The turn's answer, its cost, and its error if the last message failed."""
    text, cost, error = "", 0.0, None
    with log.open("rb") as f:
        f.seek(since)
        for line in f.read().split(b"\n"):
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict) or event.get("type") != "message_end":
                continue
            message = event.get("message")
            if not isinstance(message, dict) or message.get("role") != "assistant":
                continue
            # pi's catalog is stale; use DeepSeek's prices.
            when = datetime.fromtimestamp(message.get("timestamp", time.time() * 1000) / 1000, timezone.utc)
            cost += preflight.turn_cost(message.get("model"), message.get("usage") or {}, when)
            parts = [b.get("text", "") for b in message.get("content", []) if b.get("type") == "text"]
            if any(parts):
                text = "".join(parts)
            error = failure(message)
            if error and not any(parts):
                text = ""  # earlier filler is not the answer
    return text, cost, error


def pump(proc: subprocess.Popen, log: Path, narrator, idle: int) -> bool:
    """Narrate pi's output into the log until it ends. Returns whether it stalled."""
    fd = proc.stdout.fileno()
    pending: list[bytes] = []
    last = time.monotonic()
    with log.open("ab") as raw:
        if raw.tell() and not log.read_bytes().endswith(b"\n"):  # a killed run's partial line
            raw.write(b"\n")
        while True:
            ready, _, _ = select.select([fd], [], [], 5)
            if not ready:
                if proc.poll() is not None:  # done; a child holds stdout
                    break
                if time.monotonic() - last > idle:
                    narrator.emit("!", f"no event for {idle}s; killing pi")
                    return True
                continue
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            last = time.monotonic()
            raw.write(chunk)
            raw.flush()
            pending.append(chunk)
            if b"\n" not in chunk:  # join only once a line ends
                continue
            *lines, rest = b"".join(pending).split(b"\n")
            pending = [rest]
            for line in lines:
                if line.strip():
                    narrator.feed(line.decode("utf-8", errors="replace"))
    rest = b"".join(pending)
    if rest.strip():
        narrator.feed(rest.decode("utf-8", errors="replace"))
    return False


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
    p.add_argument("--dir", default=".", help="worker cwd (sessions are keyed by it)")
    p.add_argument("--model", default="cloud", help="LiteLLM alias (default cloud)")
    p.add_argument("--idle", type=int, default=300, help="kill after N silent seconds")
    p.add_argument("prompt", help="the question, or @file to read it from")
    args = p.parse_args()
    if not SESSION_NAME.fullmatch(args.session):
        p.error("--session takes letters, digits, '.', '_' and '-', starting and ending alphanumeric")

    if not Path(args.dir).is_dir():
        p.error(f"--dir {args.dir} is not a directory")
    prompt = args.prompt
    if prompt.startswith("@"):
        try:
            prompt = Path(prompt[1:]).expanduser().read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            p.error(f"cannot read the prompt file {prompt[1:]}: {e}")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = LOG_DIR / f"{args.session}.jsonl"
    since = log.stat().st_size if log.exists() else 0

    # Depth 1: headless hard-block mode, no git writes.
    env = dict(os.environ, PATH=f"{TOOLBOX_BIN}:{os.environ.get('PATH', '')}", PI_SUBAGENT_DEPTH="1")
    # "--": a prompt may start with - or ---.
    cmd = ["pi", "--mode", "json", "--approve", "--provider", "litellm", "--model", args.model,
           "--session-id", args.session, "--", prompt]
    # Before Popen, so no signal leaves pi orphaned.
    for sig in SIGNALS:
        signal.signal(sig, on_signal)
    try:
        # DEVNULL: pi reads piped stdin to EOF first.
        proc = subprocess.Popen(cmd, cwd=args.dir, env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                start_new_session=True)
    except FileNotFoundError:
        sys.exit("pi-ask.py: pi is not on PATH")
    except OSError as e:
        if e.errno != errno.E2BIG:
            raise
        sys.exit(f"pi-ask.py: the prompt ({len(prompt.encode())} bytes) is over the OS argument limit; shorten it")
    narrator = narrate.Narrator(label=args.session, out=sys.stdout)
    stalled = False
    try:
        _armed = True
        if _caught:
            raise Interrupted(_caught)
        stalled = pump(proc, log, narrator, args.idle)
    except Interrupted as e:
        narrator.emit("!", f"{signal.Signals(e.signum).name}; stopping pi")
    finally:
        _armed = False
        # pi has its own group, so pass our death on.
        kill_group(proc)
    code = proc.wait()
    narrator.finish()

    text, cost, error = answer_and_cost(log, since)
    print(f"\n=== answer ({args.session}, ${cost:.4f} at DeepSeek's prices, log {log}) ===")
    print(text or "(no answer)")
    if error:
        print(f"=== the last turn failed: {error} ===")
    print(f"=== follow up: pi-ask.py --session {args.session} --dir {shlex.quote(str(Path(args.dir).resolve()))} \"...\" ===")
    if _caught:
        print(f"=== stopped by {signal.Signals(_caught).name} ===")
        return 128 + _caught
    if stalled:
        return 3
    if error:
        return code or 1
    return code or (0 if text else 1)


if __name__ == "__main__":
    sys.exit(main())
