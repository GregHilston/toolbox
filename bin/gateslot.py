#!/usr/bin/env python3
"""A machine-wide counting semaphore for ./verify.sh gates.

Lanes spend most of their time coding; the gate is the one CPU-heavy step.
Each slot is a flock'd file, so a crashed holder frees its slot by dying.

    from gateslot import slot
    with slot(): ...                  # a lane gate waits for one of GATE_SLOTS
    with slot(land=True): ...         # a landing gate also has a reserved slot
    with slot(kind="worker") as gate:  # the caller then sets gate.code
        gate.code = 0

    gateslot.py [--land] [--kind K] -- ./verify.sh   # same, from a shell
    gateslot.py --report [hours]           # gate wait as a share of ticket time

GATE_SLOTS sets the count (default 2); 0 turns the queue off. Callers set
`gate.code` on the yielded object so the run log can record how it ended.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runlog  # noqa: E402

DIR = Path(os.environ.get("GATE_SLOT_DIR", Path.home() / ".cache" / "gate-slots"))
PASSED = DIR / "passed"
LOG = DIR / "gate-wait.jsonl"


def _tree(cwd=".") -> str:
    return subprocess.run(["git", "rev-parse", "HEAD^{tree}"], cwd=cwd, capture_output=True,
                          text=True, check=True).stdout.strip()


def tree_id(cwd=".") -> str:
    """The checked-out content: HEAD's tree plus any tracked edits, empty outside a repo."""
    try:
        diff = subprocess.run(["git", "diff", "HEAD"], cwd=cwd, capture_output=True, check=True).stdout
        head = _tree(cwd)
    except (OSError, subprocess.CalledProcessError):
        return ""
    return head[:12] + (hashlib.sha1(diff).hexdigest()[:8] if diff else "")


def mark_passed(cwd=".") -> None:
    """Record that the gate passed on this clean tree."""
    PASSED.mkdir(parents=True, exist_ok=True)
    (PASSED / _tree(cwd)).touch()


def already_passed(cwd=".") -> bool:
    """Whether the gate already passed on this exact tree."""
    return (PASSED / _tree(cwd)).exists()


def record(**event) -> None:
    """Append one event to the log that --report reads."""
    DIR.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps(event) + "\n")


def report(lines: list[str], since: float = 0.0) -> str:
    """Tickets an hour and the share of ticket time spent waiting for a gate slot."""
    events = [json.loads(line) for line in lines]
    tickets = [e for e in events if e["kind"] == "ticket" and e["started"] >= since]
    gates = [e for e in events if e["kind"] == "gate" and e["asked"] >= since]
    if not tickets:
        return f"no tickets in the log; {len(gates)} gates"
    span = max(t["ended"] for t in tickets) - min(t["started"] for t in tickets)
    ticket_time = sum(t["ended"] - t["started"] for t in tickets)
    wait = sum(g["got"] - g["asked"] for g in gates
               if any(t["cwd"] == g["cwd"] and t["started"] <= g["asked"] <= t["ended"] for t in tickets))
    land = [g["got"] - g["asked"] for g in gates if g["land"]]
    return (f"{len(tickets)} tickets in {span / 3600:.1f} h ({len(tickets) / max(span / 3600, 0.01):.1f} an hour); "
            f"gate wait {wait / 60:.0f} min of {ticket_time / 60:.0f} min ticket time ({wait / ticket_time:.0%}); "
            f"{len(gates)} gates, {len(land)} landing, landing wait {sum(land) / 60:.0f} min")


class Gate:
    """One slot; the caller sets `code` so the log can say how the gate ended."""

    def __init__(self, land: bool, kind: str | None) -> None:
        self.land, self.kind, self.code = land, kind, None
        self.asked = self.got = 0.0


@contextmanager
def slot(land: bool = False, poll: float = 2.0, kind: str | None = None, full: bool | None = None):
    n = int(os.environ.get("GATE_SLOTS", "2"))
    gate = Gate(land, kind or ("landing" if land else "worker"))
    gate.asked = time.time()
    runlog.emit("gate_queued", land=land, gate_kind=gate.kind)
    held = None
    if n > 0:
        DIR.mkdir(parents=True, exist_ok=True)
        while held is None:
            for i in range(n + land):
                f = open(DIR / f"{i}.lock", "w")
                try:
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    held = f
                    break
                except BlockingIOError:
                    f.close()
            else:
                time.sleep(poll)
    gate.got = time.time()
    tree = tree_id()
    runlog.emit("gate_slot", wait=round(gate.got - gate.asked, 3), land=land, gate_kind=gate.kind)
    try:
        yield gate
    finally:
        if held:
            held.close()
        if n > 0:
            record(kind="gate", cwd=os.getcwd(), land=land, asked=gate.asked, got=gate.got, ended=time.time())
        extra = {"tree": tree} if tree else {}
        if full is not None:
            extra["full"] = full
        runlog.emit("gate_done", seconds=round(time.time() - gate.got, 3), exit=gate.code, gate_kind=gate.kind,
                    **extra)


def main(args: list[str]) -> int:
    if args[:1] == ["--report"]:
        hours = float(args[1]) if len(args) > 1 else 24.0
        print(report(LOG.read_text().splitlines() if LOG.exists() else [], time.time() - hours * 3600))
        return 0
    land = args[:1] == ["--land"]
    kind = None
    if "--kind" in args[:-1]:
        kind = args[args.index("--kind") + 1]
    cmd = args[args.index("--") + 1:] if "--" in args else []
    if not cmd:
        sys.exit("usage: gateslot.py [--land] [--kind K] -- cmd... | gateslot.py --report [hours]")
    with slot(land, kind=kind, full=cmd == ["./verify.sh"]) as gate:
        gate.code = subprocess.run(cmd).returncode
        code = gate.code
    # A partial gate or dirty tree proves nothing about HEAD.
    if code == 0 and cmd == ["./verify.sh"] and not subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip():
        mark_passed()
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
