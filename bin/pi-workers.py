#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Answer "what are the pi workers doing right now" from their status files.

Every worker spawned by `/orchestrate-pi` runs with `PI_STATUS_FILE` set, and
the `orchestration-status` extension rewrites that file on every turn and every
tool call. This reads all of them at once and renders the answer three ways: a
table for a human, one line for a status bar, and JSON for an orchestrator.

It exists because the alternative — reading a 13MB JSONL log per worker — is
slow, expensive in context, and answers the wrong question. Worse, the three
failure modes that actually bite are all *absences*, and only a poller that
knows what it expected to find can see them:

  - **never started**  a `.pi/` directory with no `status.json` beside it. The
    spawn bug: the process was never created and the log sits at 0 bytes.
  - **died**           a status file whose `pid` is no longer alive. This is the
    one that fooled us twice in one run: a dead worker and a thinking worker
    look identical from outside, so both got reported as "still running".
  - **stalled**        `lastActivityAt` gone cold while the phase says working.

Usage:
    pi-workers.py                      # table, discovered from the cwd
    pi-workers.py --oneline            # one compact line, empty if no workers
    pi-workers.py --json               # machine-readable
    pi-workers.py --watch              # live table, for a second terminal
    pi-workers.py --root ~/Git/gridkeep
    pi-workers.py --strict             # exit 1 if any worker needs attention

Discovery looks for directories containing a `.pi/` under `<root>/worktrees/*`,
`<root>/.claude/worktrees/*` and `<root>` itself. Pass paths explicitly to skip
discovery entirely.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import signal
import sys
import time
from pathlib import Path
from typing import Any

# A worker whose last event is older than this while it still claims to be
# working is stuck, not slow. Set from the longest legitimate quiet stretch seen
# in a real run: a Pro `max` thinking turn plus a full GUT suite is comfortably
# under two minutes.
DEFAULT_STALL_SECONDS = 120.0

# Phases the extension publishes that mean the worker is finished, not silent.
TERMINAL_PHASES = frozenset({"settled", "shutdown"})

STATE_SYMBOLS = {
    "tool": "▸",
    "thinking": "~",
    "starting": "○",
    "done": "✓",
    "stalled": "⏸",
    "dead": "✗",
    "nostart": "∅",
}


def process_alive(pid: Any) -> bool | None:
    """None when we cannot tell — a missing pid is not evidence of death."""
    if not isinstance(pid, int) or pid <= 0:
        return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Alive, owned by someone else. Cannot happen for our own workers, but
        # reporting "dead" here would be a lie.
        return True
    except OSError:
        return None
    return True


def parse_timestamp(value: Any) -> dt.datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        stamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is None:
        # The extension writes toISOString(), which always carries the Z. A
        # naive stamp means a hand-edited or foreign file, and subtracting it
        # from an aware `now` raises TypeError — which would take down the whole
        # table over one bad file. Assume UTC, which is what the writer means.
        return stamp.replace(tzinfo=dt.UTC)
    return stamp


def discover(roots: list[Path]) -> list[Path]:
    """Directories that look like a pi worker: they have a `.pi/` in them.

    `.pi/` is what the orchestrator writes before spawning (the permission
    config and the guardrails file), so it exists even for a worker that never
    started — which is exactly the case worth reporting.
    """
    found: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        candidates = [root]
        for pattern in ("worktrees/*", ".claude/worktrees/*"):
            candidates.extend(sorted(root.glob(pattern)))
        for candidate in candidates:
            try:
                if not (candidate / ".pi").is_dir():
                    continue
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            found.append(candidate)
    return found


def read_worker(directory: Path, now: dt.datetime, stall_seconds: float) -> dict[str, Any]:
    """Reduce one worker's status file to the fields a poller actually asks for."""
    name = directory.name
    path = directory / ".pi" / "status.json"
    worker: dict[str, Any] = {
        "name": name,
        "dir": str(directory),
        "state": "nostart",
        "turn": None,
        "toolCalls": None,
        "ageSeconds": None,
        "costUsd": None,
        "doing": "no status file — it never started",
        "pid": None,
        "needsAttention": True,
    }
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return worker
    except OSError as exc:
        worker["doing"] = f"status file unreadable: {exc}"
        return worker

    try:
        status = json.loads(raw)
    except ValueError:
        # The writes are atomic (temp + rename), so this is corruption rather
        # than a torn read, and saying so is more useful than retrying.
        worker["state"] = "unknown"
        worker["doing"] = "status file is not valid JSON"
        return worker
    if not isinstance(status, dict):
        worker["state"] = "unknown"
        worker["doing"] = "status file is not an object"
        return worker

    phase = str(status.get("phase", "unknown"))
    usage = status.get("usage") if isinstance(status.get("usage"), dict) else {}
    worker.update(
        {
            "turn": status.get("turn"),
            "toolCalls": status.get("toolCalls"),
            "costUsd": usage.get("costUsd"),
            "totalTokens": usage.get("totalTokens"),
            "pid": status.get("pid"),
            "model": status.get("model"),
            "lastBlocked": status.get("lastBlocked"),
        }
    )

    last = parse_timestamp(status.get("lastActivityAt"))
    age = (now - last).total_seconds() if last is not None else None
    worker["ageSeconds"] = age

    alive = process_alive(status.get("pid"))
    if phase in TERMINAL_PHASES:
        worker["state"] = "done"
    elif alive is False:
        worker["state"] = "dead"
    elif age is not None and age > stall_seconds:
        worker["state"] = "stalled"
    else:
        worker["state"] = phase

    worker["needsAttention"] = worker["state"] in ("dead", "stalled", "nostart", "unknown")
    worker["doing"] = describe(status, worker)
    return worker


def describe(status: dict[str, Any], worker: dict[str, Any]) -> str:
    """The 'doing' column: the most specific thing we can say in one line."""
    state = worker["state"]
    if state == "dead":
        return f"process {status.get('pid')} is gone — read the log before respawning"
    if state == "stalled":
        return f"no activity for {int(worker['ageSeconds'] or 0)}s while phase={status.get('phase')}"
    tool = status.get("currentTool")
    if state == "tool" and tool:
        detail = str(status.get("lastToolBrief") or "").strip()
        return f"{tool} {detail}".strip()
    said = str(status.get("lastText") or "").strip()
    if said:
        return f"» {said}"
    if state == "done":
        return "finished — verify the branch"
    return str(status.get("phase", ""))


def gather(paths: list[Path], stall_seconds: float) -> list[dict[str, Any]]:
    now = dt.datetime.now(dt.UTC)
    return [read_worker(path, now, stall_seconds) for path in paths]


def render_table(workers: list[dict[str, Any]], width: int) -> str:
    if not workers:
        return "No pi workers found. Looked for directories containing a .pi/ directory."
    header = f"{'worker':<20} {'state':<9} {'turn':>4} {'tools':>5} {'age':>7} {'cost':>9}  doing"
    rows = [header, "-" * min(len(header) + 20, width)]
    for worker in workers:
        symbol = STATE_SYMBOLS.get(worker["state"], " ")
        turn = "-" if worker["turn"] is None else str(worker["turn"])
        tools = "-" if worker["toolCalls"] is None else str(worker["toolCalls"])
        age = "-" if worker["ageSeconds"] is None else f"{int(worker['ageSeconds'])}s"
        cost = "-" if worker["costUsd"] is None else f"${worker['costUsd']:.4f}"
        prefix = (
            f"{worker['name'][:20]:<20} {symbol}{worker['state']:<8} "
            f"{turn:>4} {tools:>5} {age:>7} {cost:>9}  "
        )
        rows.append((prefix + worker["doing"])[:width])
    trouble = [w["name"] for w in workers if w["needsAttention"]]
    if trouble:
        rows.append("")
        rows.append(f"Needs attention: {', '.join(trouble)}")
    return "\n".join(rows)


def render_oneline(workers: list[dict[str, Any]]) -> str:
    """Empty when there is nothing to say, so a status bar hides the widget."""
    live = [w for w in workers if w["state"] not in ("done",)]
    if not workers or (not live and not any(w["needsAttention"] for w in workers)):
        return ""
    counts: dict[str, int] = {}
    for worker in workers:
        counts[worker["state"]] = counts.get(worker["state"], 0) + 1
    parts = [f"pi {len(workers)}w"]
    for state in ("tool", "thinking", "starting", "done"):
        if counts.get(state):
            parts.append(f"{counts[state]}{STATE_SYMBOLS.get(state, state)}")
    cost = sum(w["costUsd"] or 0.0 for w in workers)
    if cost:
        parts.append(f"${cost:.4f}")
    for state in ("stalled", "dead", "nostart"):
        if counts.get(state):
            parts.append(f"⚠{counts[state]} {state}")
    return " ".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report on running pi workers.")
    parser.add_argument("paths", nargs="*", help="Worker directories. Skips discovery.")
    parser.add_argument(
        "--root",
        action="append",
        default=None,
        help="Where to discover workers (repeatable). Default: $PI_WORKERS_ROOT, else cwd.",
    )
    parser.add_argument("--oneline", action="store_true", help="One compact line for a status bar.")
    parser.add_argument("--json", action="store_true", help="Machine-readable output.")
    parser.add_argument("--watch", action="store_true", help="Redraw the table until interrupted.")
    parser.add_argument("--interval", type=float, default=3.0, help="--watch redraw seconds.")
    parser.add_argument(
        "--stall-seconds",
        type=float,
        default=DEFAULT_STALL_SECONDS,
        help=f"Call a quiet worker stalled after this long (default {DEFAULT_STALL_SECONDS:g}).",
    )
    parser.add_argument("--width", type=int, default=0, help="Truncate rows (default: terminal).")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if any worker needs attention, 2 if none were found.",
    )
    parser.add_argument(
        "--from-statusline",
        action="store_true",
        help="Read Claude Code's status-line JSON on stdin and take roots from it.",
    )
    args = parser.parse_args(argv)

    roots: list[Path] = []
    if args.from_statusline:
        # ccstatusline always pipes a JSON payload; a malformed one must not
        # turn the status bar into an error message.
        try:
            payload = json.loads(sys.stdin.read() or "{}")
        except ValueError:
            payload = {}
        if isinstance(payload, dict):
            workspace = payload.get("workspace") if isinstance(payload.get("workspace"), dict) else {}
            for key, source in (("cwd", payload), ("project_dir", workspace), ("current_dir", workspace)):
                value = source.get(key)
                if isinstance(value, str) and value:
                    roots.append(Path(value))
    for value in args.root or []:
        roots.append(Path(os.path.expanduser(value)))
    if not roots:
        env_root = os.environ.get("PI_WORKERS_ROOT")
        roots = [Path(os.path.expanduser(env_root))] if env_root else [Path.cwd()]

    explicit = [Path(os.path.expanduser(p)) for p in args.paths]
    width = args.width or shutil.get_terminal_size((160, 24)).columns

    def snapshot() -> list[dict[str, Any]]:
        paths = explicit or discover(roots)
        return gather(paths, args.stall_seconds)

    if args.watch:
        try:
            while True:
                workers = snapshot()
                print("\033[2J\033[H", end="")
                print(time.strftime("%H:%M:%S"), "— pi workers")
                print(render_table(workers, width))
                time.sleep(args.interval)
        except KeyboardInterrupt:
            return 0

    workers = snapshot()
    if args.json:
        print(json.dumps(workers, indent=2))
    elif args.oneline:
        line = render_oneline(workers)
        if line:
            print(line)
    else:
        print(render_table(workers, width))

    if args.strict:
        if not workers:
            return 2
        if any(worker["needsAttention"] for worker in workers):
            return 1
    return 0


if __name__ == "__main__":
    # A status bar re-runs this constantly; a SIGPIPE traceback there is noise.
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    sys.exit(main())
