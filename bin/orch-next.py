#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Start a fresh orchestrator session from a handoff file, in a session Greg can open.

An orchestrator past its context cap writes a handoff whose last fenced code
block is the exact first message for the next chat, then runs:

    orch-next.py HANDOFF.md [--repo DIR] [--dry-run]

This starts an interactive `claude --bg --remote-control` session in the repo
with that message. Greg types to it from moria (`claude attach ID`) or from
claude.ai/code and the phone app (the URL printed here). The new session reads
lane state from disk (`lane.py status`, `.git/land/`); it inherits no context.
One session per repo: a live earlier start makes this refuse and name it.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

STATE = Path.home() / ".cache" / "orch-next"
URL_RE = re.compile(r"https://claude\.ai/code/session_\w+")
ID_RE = re.compile(r"backgrounded\s*\W+\s*(\w+)")
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


def live_ids(repo: Path) -> set[str]:
    """Ids of the repo's live background sessions; a stopped one drops out."""
    out = subprocess.run(["claude", "agents", "--json", "--cwd", str(repo)], capture_output=True, text=True)
    try:
        return {a["id"] for a in json.loads(out.stdout) if a.get("kind") == "background"}
    except (ValueError, KeyError, TypeError):
        return set()


def session_url(sid: str, wait: float = 20.0) -> str | None:
    """The claude.ai URL the session prints once Remote Control connects."""
    deadline = time.monotonic() + wait
    while True:
        out = subprocess.run(["claude", "logs", sid], capture_output=True, text=True)
        if m := URL_RE.search(out.stdout):
            return m.group(0)
        if time.monotonic() >= deadline:
            return None
        time.sleep(2)


def command(handoff: Path, message: str, name: str) -> list[str]:
    """The claude invocation; the handoff path is named so the new session reads it."""
    prompt = f"{PREAMBLE}Handoff: {handoff}\n\n{message}"
    return ["claude", "--bg", "--remote-control", name, "-n", name, "--permission-mode", "auto", prompt]


def start(handoff: Path, repo: Path, dry_run: bool = False) -> str:
    """Launch the successor and return where it is and how to stop it."""
    handoff = handoff.resolve()
    name = f"orchestrator-{repo.name}-{time.strftime('%m%d-%H%M')}"
    cmd = command(handoff, first_message(handoff), name)
    if dry_run:
        return f"would run in {repo}: {' '.join(cmd[:7])} <prompt of {len(cmd[7])} chars>"
    STATE.mkdir(parents=True, exist_ok=True)
    id_file = STATE / f"{repo.name}.id"
    if id_file.exists() and (old := id_file.read_text().strip()) in live_ids(repo):
        raise HandoffError(f"orchestrator {old} is already running in {repo}; "
                           f"open it with `claude attach {old}` or stop it with `claude stop {old}`")
    out = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    m = ID_RE.search(out.stdout)
    if out.returncode or not m:
        raise HandoffError(f"claude did not start a background session: {(out.stdout + out.stderr).strip()}")
    sid = m.group(1)
    id_file.write_text(f"{sid}\n")
    url = session_url(sid)
    return (f"started {name} (id {sid}) in {repo}\n"
            f"  phone or browser: {url or 'URL not up yet; run `claude logs ' + sid + '`'}\n"
            f"  moria: claude attach {sid}   output so far: claude logs {sid}\n"
            f"  stop: claude stop {sid}")


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
