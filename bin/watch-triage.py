#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Print only the `lane.py watch` events that need a Claude decision.

    lane.py watch | watch-triage.py

Every line the monitor prints wakes the orchestrator for a full turn. A park, a
stop and an unclassified line wake it at once. A landing, a gate failure (the
loop fixes it) and a batch of lane starts are held and ride along with the next
wake line as one summary. A line this script has no rule for goes to DeepSeek
(pi-ask.py) for WAKE or QUIET; if that fails, it wakes. At the end it prints
how many events came in and how many woke.
"""

from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

PI_ASK = Path(__file__).resolve().parent / "pi-ask.py"
QUIET = (re.compile(r"^landed: "), re.compile(r"^lane \S+ gate FAIL"), re.compile(r"^lane starts:"))
WAKE = (re.compile(r"^lane \S+ parked "), re.compile(r"^lane \S+ stopped: "))
ASK = (
    "A monitor of overnight coding lanes printed this event:\n{line}\n"
    "Answer WAKE if a human-level orchestrator must decide something now (a park, a stop, a red main, "
    "a landing that needs review), otherwise QUIET. One word."
)


def classify(line: str) -> str:
    """wake, quiet or unknown, by the first line of the event."""
    if any(p.match(line) for p in WAKE):
        return "wake"
    if any(p.match(line) for p in QUIET):
        return "quiet"
    return "unknown"


def ask_deepseek(line: str) -> str:
    """wake or quiet from DeepSeek; wake when it fails or says anything else."""
    session = f"gk-triage-{int(time.time())}"
    try:
        out = subprocess.run([str(PI_ASK), "--session", session, "--max-turns", "3", ASK.format(line=line)],
                             capture_output=True, text=True, timeout=300).stdout
    except (OSError, subprocess.TimeoutExpired):
        return "wake"
    return "quiet" if "QUIET" in out and "WAKE" not in out else "wake"


class Triage:
    """Groups indented lines with their event and holds quiet ones for the next wake."""

    def __init__(self, ask=ask_deepseek) -> None:
        self.ask, self.held, self.events, self.wakes = ask, [], 0, 0

    def event(self, text: str) -> str | None:
        """The text to print for one event, or None to stay quiet."""
        self.events += 1
        kind = classify(text.splitlines()[0])
        if kind == "unknown":
            kind = self.ask(text)
        if kind == "quiet":
            self.held.append(text.splitlines()[0])
            return None
        self.wakes += 1
        held, self.held = self.held, []
        prefix = f"({len(held)} quiet: {'; '.join(held)})\n" if held else ""
        return prefix + text

    def summary(self) -> str:
        return f"watch-triage: {self.events} events, {self.wakes} wake-ups, {self.events - self.wakes} held"


def run(lines, out=sys.stdout, ask=ask_deepseek) -> Triage:
    """Triage an iterable of watch lines, printing wake events as they close."""
    triage, block = Triage(ask), []

    def flush() -> None:
        if block:
            text = triage.event("\n".join(block))
            if text:
                print(text, file=out, flush=True)
            block.clear()

    for line in lines:
        line = line.rstrip("\n")
        if line[:1] in (" ", "\t") and block:
            block.append(line)
            continue
        flush()
        if line.strip():
            block.append(line)
    flush()
    return triage


def main() -> int:
    try:
        triage = run(sys.stdin)
    except KeyboardInterrupt:
        return 130
    print(triage.summary(), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
