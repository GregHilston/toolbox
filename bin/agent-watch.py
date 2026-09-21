#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Show what a running Hermes iteration is actually doing.

`docker logs` on a run is 59 lines of gateway boot noise and then silence: the
worker's transcript is never persisted, and `hermes kanban log` stays empty. The
signals that do exist are scattered — heartbeats in kanban.db, files appearing on
the bind mount, and completions in oMLX's log — and all three are readable from
the host, so watching costs the run nothing.

Traffic comes from the log rather than `~/.omlx/stats.json`, which flushes lazily
with an unbounded lag: it was seen sitting at 1240 requests while the log showed
eleven completions in the previous six minutes.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

RUNS = Path.home() / "Git/agent-runs/iter"
OMLX_LOG = Path.home() / "Library/Logs/omlx.log"
SKIP = {".venv", "node_modules", "__pycache__", ".git", ".ruff_cache", ".pytest_cache"}


def ago(seconds: float) -> str:
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m{seconds % 60:02d}s"
    return f"{seconds // 3600}h{(seconds % 3600) // 60:02d}m"


LINE = re.compile(
    r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),\d+ .*"
    r"Chat completion: model=([^,]+), (\d+) tokens in ([\d.]+)s .*prompt: (\d+)"
)


def log_traffic(since_epoch: float) -> dict:
    """Per-model totals since a run started, read from oMLX's own log.

    `~/.omlx/stats.json` is the obvious source and it cannot be trusted for this:
    it flushes lazily with an unbounded lag, and was observed sitting at 1240
    requests while the log showed eleven completions in the previous six minutes.
    A watcher reading it says "no model traffic yet" about a run that is working.
    """
    stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(since_epoch))
    agg: dict[str, dict] = {}
    try:
        with open(OMLX_LOG, errors="ignore") as fh:
            for line in fh:
                m = LINE.match(line)
                if not m or m.group(1) < stamp:
                    continue
                a = agg.setdefault(m.group(2), {"reqs": 0, "prompt": 0,
                                                "completion": 0, "secs": 0.0})
                a["reqs"] += 1
                a["prompt"] += int(m.group(5))
                a["completion"] += int(m.group(3))
                a["secs"] += float(m.group(4))
    except OSError:
        return {}
    return agg


def kanban(instance: Path) -> dict:
    """Read the board read-only — a writer lock here would stall the dispatcher."""
    db = instance / "home/kanban.db"
    if not db.exists():
        return {}
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2)
        conn.row_factory = sqlite3.Row
    except Exception as exc:
        return {"error": str(exc)}
    out: dict = {}
    try:
        task = conn.execute("select id, title, status from tasks order by rowid limit 1").fetchone()
        if task:
            out["task"] = dict(task)
        run = conn.execute(
            "select id, profile, status, started_at, last_heartbeat_at, outcome, error"
            " from task_runs order by rowid desc limit 1"
        ).fetchone()
        if run:
            out["run"] = dict(run)
        out["events"] = [
            dict(r) for r in conn.execute(
                "select kind, payload, created_at from task_events order by id desc limit 200"
            )
        ]
    except Exception as exc:
        out["error"] = str(exc)
    finally:
        conn.close()
    return out


def workspace_state(instance: Path) -> dict:
    ws = instance / "workspace"
    files, loc, newest, newest_path = 0, 0, 0.0, None
    for p in ws.rglob("*.py") if ws.is_dir() else []:
        if any(part in SKIP for part in p.parts):
            continue
        files += 1
        try:
            loc += sum(1 for line in p.read_text(errors="ignore").splitlines() if line.strip())
            if p.stat().st_mtime > newest:
                newest, newest_path = p.stat().st_mtime, p.relative_to(ws)
        except OSError:
            pass
    return {"files": files, "loc": loc, "newest": newest, "newest_path": newest_path}


def model_lines(traffic: dict, elapsed: float) -> list[str]:
    lines = []
    for model, a in sorted(traffic.items(), key=lambda kv: -kv[1]["reqs"]):
        n = a["reqs"]
        if not n:
            continue
        rpm = n / (elapsed / 60) if elapsed > 0 else 0
        lines.append(
            f"  {model}: {n} reqs ({rpm:.1f}/min), "
            f"{a['prompt'] / n / 1000:.1f}k avg prompt, "
            f"{a['completion'] / n:.0f} avg completion, "
            f"{a['secs']:.0f}s of model time"
        )
    return lines


def last_completion(since_epoch: float) -> float:
    """Epoch of the most recent completion, or the run start if there is none."""
    stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(since_epoch))
    latest = since_epoch
    try:
        with open(OMLX_LOG, errors="ignore") as fh:
            for line in fh:
                m = LINE.match(line)
                if m and m.group(1) >= stamp:
                    latest = time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"))
    except OSError:
        pass
    return latest


def render(instance: Path) -> str:
    board = kanban(instance)
    if "error" in board and "task" not in board:
        return f"{instance.name}: board unreadable ({board['error']})"

    task, run = board.get("task") or {}, board.get("run") or {}
    events = board.get("events") or []
    now = time.time()
    started = float(run.get("started_at") or 0)
    elapsed = now - started if started else 0

    out = [
        f"{instance.name}  card={task.get('status', '?')}  "
        f"run {run.get('id', '?')} {run.get('profile', '?')} {run.get('status', '?')}  "
        f"elapsed {ago(elapsed)}"
    ]
    if run.get("error"):
        out.append(f"  error: {run['error']}")
    if run.get("outcome"):
        out.append(f"  outcome: {run['outcome']}")

    hb = float(run.get("last_heartbeat_at") or 0)
    if hb:
        out.append(f"  heartbeat {ago(now - hb)} ago")
    # Heartbeat notes are the worker's only self-report; most carry no payload.
    for e in events:
        if e["kind"] == "heartbeat" and e["payload"]:
            try:
                note = json.loads(e["payload"]).get("note")
            except Exception:
                note = None
            if note:
                out.append(f"  last note ({ago(now - e['created_at'])} ago): {note}")
                break
    kinds = [e["kind"] for e in events if e["kind"] != "heartbeat"]
    if kinds:
        out.append("  events: " + ", ".join(reversed(kinds[:12])))

    ws = workspace_state(instance)
    if ws["files"]:
        out.append(
            f"  workspace: {ws['files']} .py files, {ws['loc']} LOC, "
            f"last write {ago(now - ws['newest'])} ago ({ws['newest_path']})"
        )
    else:
        out.append("  workspace: no python files yet")

    # Present only once the run has been scored, so this doubles as "is it done".
    score_path = instance / "score.json"
    if score_path.exists():
        try:
            s = json.loads(score_path.read_text())
            out.append(
                f"  SCORED: tests {s.get('tests_passed')} pass / {s.get('tests_failed')} fail, "
                f"build exit {s.get('build_exit_code')}, dataset rows {s.get('dataset_rows')}, "
                f"package {s.get('package_found') or 'none'}"
            )
            for note in s.get("notes") or []:
                out.append(f"    note: {note}")
        except Exception as exc:
            out.append(f"  score.json unreadable ({exc})")

    traffic = log_traffic(started) if started else {}
    out += model_lines(traffic, elapsed) or ["  no model traffic yet"]
    # Silence is the failure mode that matters: run gate-a heartbeated for 51
    # minutes while serving nothing for twenty of them.
    if traffic:
        quiet = now - last_completion(started)
        if quiet > 300:
            out.append(f"  !! no completion for {ago(quiet)} — possible stall")

    return "\n".join(out)


def newest_instance() -> Path | None:
    candidates = [p for p in RUNS.iterdir() if (p / "home/kanban.db").exists()] if RUNS.is_dir() else []
    return max(candidates, key=lambda p: (p / "home/kanban.db").stat().st_mtime, default=None)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("name", nargs="?", help="iteration name (default: the most recently active)")
    ap.add_argument("-f", "--follow", action="store_true")
    ap.add_argument("--interval", type=float, default=20.0)
    args = ap.parse_args()

    instance = RUNS / args.name if args.name else newest_instance()
    if instance is None or not instance.is_dir():
        print(f"no such iteration: {args.name or '(none found)'}", file=sys.stderr)
        return 2

    while True:
        print(render(instance), flush=True)
        if not args.follow:
            return 0
        time.sleep(args.interval)
        print(flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
