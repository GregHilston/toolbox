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
import importlib.util
import json
import os
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


def answer_and_cost(log: Path, since: int) -> tuple[str, float]:
    text, cost = "", 0.0
    with log.open("rb") as f:
        f.seek(since)
        for line in f.read().split(b"\n"):
            try:
                event = json.loads(line)
            except ValueError:
                continue
            message = event.get("message") if isinstance(event, dict) else None
            if event.get("type") != "message_end" or not isinstance(message, dict):
                continue
            if message.get("role") != "assistant":
                continue
            # pi's own cost uses a stale catalog; price it from DeepSeek's table.
            when = datetime.fromtimestamp(message.get("timestamp", time.time() * 1000) / 1000, timezone.utc)
            cost += preflight.turn_cost(message.get("model"), message.get("usage") or {}, when)
            parts = [b.get("text", "") for b in message.get("content", []) if b.get("type") == "text"]
            if any(parts):
                text = "".join(parts)
    return text, cost


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--session", required=True, help="name; reuse it to follow up")
    p.add_argument("--dir", default=".", help="worker cwd (sessions are keyed by it)")
    p.add_argument("--model", default="cloud", help="LiteLLM alias (default cloud)")
    p.add_argument("--idle", type=int, default=300, help="kill after N silent seconds")
    p.add_argument("prompt", help="the question, or @file to read it from")
    args, pi_extra = p.parse_known_args()

    prompt = args.prompt
    if prompt.startswith("@"):
        prompt = Path(prompt[1:]).expanduser().read_text(encoding="utf-8")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = LOG_DIR / f"{args.session}.jsonl"
    since = log.stat().st_size if log.exists() else 0

    # Depth 1: bash-guard hard-blocks only catastrophes, never prompts.
    env = dict(os.environ, PATH=f"{TOOLBOX_BIN}:{os.environ.get('PATH', '')}", PI_SUBAGENT_DEPTH="1")
    cmd = ["pi", "--mode", "json", "--approve", "--provider", "litellm", "--model", args.model,
           "--session-id", args.session, *pi_extra, prompt]
    # stdin=DEVNULL: pi reads piped stdin to EOF before anything else.
    proc = subprocess.Popen(cmd, cwd=args.dir, env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            start_new_session=True)
    narrator = narrate.Narrator(label=args.session, out=sys.stdout)
    fd = proc.stdout.fileno()
    buffer, last, stalled = b"", time.monotonic(), False
    with log.open("ab") as raw:
        while True:
            ready, _, _ = select.select([fd], [], [], 5)
            if not ready:
                if time.monotonic() - last > args.idle:
                    stalled = True
                    narrator.emit("!", f"no event for {args.idle}s; killing pi")
                    os.killpg(proc.pid, signal.SIGTERM)
                    try:
                        proc.wait(10)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
                    break
                continue
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            last = time.monotonic()
            raw.write(chunk)
            raw.flush()
            buffer += chunk
            *lines, buffer = buffer.split(b"\n")  # LF only, per pi's rpc.md
            for line in lines:
                if line.strip():
                    narrator.feed(line.decode("utf-8", errors="replace"))
    code = proc.wait()
    narrator.finish()

    text, cost = answer_and_cost(log, since)
    print(f"\n=== answer ({args.session}, ${cost:.4f}, log {log}) ===")
    print(text or "(no answer)")
    print(f"=== follow up: pi-ask.py --session {args.session} --dir {Path(args.dir).resolve()} \"...\" ===")
    if stalled:
        return 3
    return code or (0 if text else 1)


if __name__ == "__main__":
    sys.exit(main())
