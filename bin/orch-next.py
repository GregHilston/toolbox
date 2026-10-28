#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Start a fresh orchestrator session from a handoff file, detached.

An orchestrator past its context cap writes a handoff whose last fenced code
block is the exact first message for the next chat, then runs:

    orch-next.py HANDOFF.md [--repo DIR] [--dry-run]

This runs `claude -p` in the repo with that message, in the background, and
logs to ~/.cache/orch-next/. The new session reads lane state from disk
(`lane.py status`, `.git/land/`); it inherits no context. One session at a
time: a live earlier start makes this refuse, so a loop can't fork sessions.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

STATE = Path.home() / ".cache" / "orch-next"
PREAMBLE = (
    "You are the orchestrator's successor. The previous session hit its context cap and handed off. "
    "Lane state is on disk: run `lane.py status` and read the handoff before acting. "
    "Never stash, delete, or kill processes by name.\n\n"
)


class HandoffError(Exception):
    pass


def first_message(handoff: Path) -> str:
    """The handoff's last fenced code block: the message to start the next chat."""
    try:
        text = handoff.read_text()
    except OSError as e:
        raise HandoffError(f"cannot read the handoff {handoff}: {e}") from e
    blocks = re.findall(r"^```[\w-]*\n(.*?)^```", text, re.S | re.M)
    if not blocks or not blocks[-1].strip():
        raise HandoffError(f"{handoff} ends with no fenced code block holding the first message")
    return blocks[-1].strip()


def running(pid_file: Path) -> int | None:
    """The pid of a live earlier start, or None."""
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
    except (OSError, ValueError):
        return None
    return pid


def command(handoff: Path, message: str) -> list[str]:
    """The claude invocation; the handoff path is named so the new session reads it."""
    prompt = f"{PREAMBLE}Handoff: {handoff}\n\n{message}"
    return ["claude", "-p", prompt, "--permission-mode", "auto", "--permission-prompts", "none"]


def start(handoff: Path, repo: Path, dry_run: bool = False) -> str:
    """Launch the successor detached and return what to tell the user."""
    handoff = handoff.resolve()
    cmd = command(handoff, first_message(handoff))
    if dry_run:
        return "would run in " + str(repo) + ": " + " ".join(cmd[:2]) + " <prompt of " + str(len(cmd[2])) + " chars>"
    STATE.mkdir(parents=True, exist_ok=True)
    pid_file = STATE / "pid"
    if pid := running(pid_file):
        raise HandoffError(f"an earlier successor is still running (pid {pid}); not starting another")
    log = STATE / f"{time.strftime('%Y%m%d-%H%M%S')}.log"
    with log.open("ab") as out:
        proc = subprocess.Popen(cmd, cwd=repo, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                                start_new_session=True)
    pid_file.write_text(f"{proc.pid}\n")
    return f"started pid {proc.pid} in {repo}; log {log}"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("handoff", type=Path)
    p.add_argument("--repo", type=Path, default=Path.cwd(), help="working directory for the new session (default .)")
    p.add_argument("--dry-run", action="store_true", help="check the handoff and print what would run")
    args = p.parse_args(argv)
    try:
        print(start(args.handoff, args.repo.resolve(), args.dry_run))
    except HandoffError as e:
        print(f"orch-next.py: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
