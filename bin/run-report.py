#!/usr/bin/env python3
"""Print where a swarm run's time went, from runlog.py's JSON lines.

    run-report.py <run> [<run> ...]

Each ticket's time is split by intervals (its phase_start/phase_end, gates,
tests, landing), and whatever no interval covers is unexplained. "queue" is a
work gate's wait for a slot; "gate wait" is a landing gate's. A run's last
ticket extends to its lane's landing, so the landing is charged to it.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runlog

CATS = ["queue", "LLM", "own tests", "gate wait", "gate run", "review", "fix", "landing", "unexplained"]
PRIORITY = {"LLM": 1, "fix": 2, "review": 3, "landing": 4, "queue": 5, "gate wait": 6,
            "gate run": 7, "own tests": 8}
PHASE_CAT = {"plan": "LLM", "worker": "LLM", "retry": "LLM", "reviewer": "review",
             "review": "review", "fix": "fix"}


def find_log(run: str) -> Path | None:
    """A run's log, preferring this repo's directory."""
    preferred = runlog.log_path(run)
    if preferred.exists():
        return preferred
    try:
        for path in sorted(runlog.base_dir().glob(f"*/{run}.jsonl")):
            return path
    except OSError:
        pass
    return None


def read(path: Path) -> list[dict]:
    events = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and isinstance(event.get("t"), (int, float)):
            events.append(event)
    return sorted(events, key=lambda e: e["t"])


def ticket_of(event: dict) -> str | None:
    value = event.get("ticket")
    return None if value in (None, "") else str(value)


def lane_of(event: dict) -> str:
    return event.get("lane") or ""


def cached(event: dict) -> bool:
    value = event.get("cached", True)
    if isinstance(value, bool):
        return value
    return str(value).lower() not in ("", "false", "0", "no")


def activity(events: list[dict]) -> list[dict]:
    """The events that describe the run; later samples must not stretch it."""
    return [event for event in events if event["kind"] != "machine"] or events


def tickets(events: list[dict]) -> list[list]:
    """One [lane, ticket, start, end] per ticket_start, extended to the lane's landing."""
    rows: list[list] = []
    opened: dict[str, tuple[str | None, float]] = {}
    for event in events:
        lane = lane_of(event)
        if event["kind"] == "ticket_start":
            if lane in opened:
                ticket, start = opened.pop(lane)
                rows.append([lane, ticket, start, event["t"]])
            opened[lane] = (ticket_of(event), event["t"])
        elif event["kind"] == "ticket_done" and lane in opened:
            ticket, start = opened.pop(lane)
            rows.append([lane, ticket, start, event["t"]])
    finish = activity(events)[-1]["t"] if events else 0.0
    for lane, (ticket, start) in opened.items():
        rows.append([lane, ticket, start, finish])
    rows.sort(key=lambda row: row[2])
    if not rows:
        return rows
    lands: dict[str, tuple[float, float | None]] = {}
    for event in events:
        lane = lane_of(event)
        if event["kind"] == "land_start":
            lands[lane] = (event["t"], None)
        elif event["kind"] == "land_done" and lane in lands:
            lands[lane] = (lands[lane][0], event["t"])
    last: dict[str, list] = {}
    for row in rows:
        last[row[0]] = row
    for lane, row in last.items():
        land = lands.get(lane)
        if land and land[1] and land[0] >= row[3]:
            row[3] = max(row[3], land[1])
    return rows


def segments(events: list[dict]) -> list[tuple[float, float, str, str, str | None]]:
    """(start, end, category, lane, ticket) for every paired interval."""
    out: list[tuple[float, float, str, str, str | None]] = []
    phases: dict[tuple, float] = {}
    queued: dict[str, tuple[float, str | None]] = {}
    running: dict[str, float] = {}
    lands: dict[str, float] = {}
    for event in events:
        lane, kind, ticket = lane_of(event), event["kind"], ticket_of(event)
        if kind == "phase_start":
            phases[(lane, ticket, event.get("phase"))] = event["t"]
        elif kind == "phase_end":
            key = (lane, ticket, event.get("phase"))
            start = phases.pop(key, None)
            cat = PHASE_CAT.get(str(event.get("phase")))
            if start is not None and cat:
                out.append((start, event["t"], cat, lane, ticket))
        elif kind == "gate_queued":
            queued[lane] = (event["t"], ticket)
        elif kind == "gate_slot":
            if lane in queued:
                start, queued_ticket = queued.pop(lane)
                out.append((start, event["t"], "gate wait" if event.get("land") else "queue",
                            lane, queued_ticket or ticket))
            running[lane] = event["t"]
        elif kind == "gate_done" and lane in running:
            out.append((running.pop(lane), event["t"], "gate run", lane, ticket))
        elif kind == "test_run":
            seconds = float(event.get("seconds") or event.get("duration") or 0)
            if seconds > 0:
                end = float(event.get("ended") or event["t"])
                out.append((end - seconds, end, "own tests", lane, ticket))
        elif kind == "land_start":
            lands[lane] = event["t"]
        elif kind == "land_done" and lane in lands:
            out.append((lands.pop(lane), event["t"], "landing", lane, None))
    return out


def attribute(rows: list[list], segs: list[tuple]) -> dict:
    totals = Counter({cat: 0.0 for cat in CATS})
    by_lane: dict[str, list[tuple]] = defaultdict(list)
    for seg in segs:
        by_lane[seg[3]].append(seg)
    for lane, ticket, start, end in rows:
        owner: dict[int, str] = {}
        for seg_start, seg_end, cat, seg_lane, seg_ticket in by_lane.get(lane, []):
            if seg_ticket not in (None, ticket):
                continue
            low, high = max(seg_start, start), min(seg_end, end)
            if high <= low:
                continue
            rank = PRIORITY[cat]
            for second in range(int(low), int(high)):
                if rank > PRIORITY.get(owner.get(second, ""), 0):
                    owner[second] = cat
        totals.update(owner.values())
        totals["unexplained"] += max(0, int(end) - int(start) - len(owner))
    return totals


def human(seconds: float) -> str:
    if seconds >= 3600:
        return f"{seconds / 3600:.1f}h"
    if seconds >= 60:
        return f"{seconds / 60:.0f}m"
    return f"{seconds:.0f}s"


def ticket_costs(events: list[dict]) -> dict[str, tuple[int, float, int, int]]:
    """(tickets, list-price dollars, tokens, tickets with cost) per outcome.

    A ticket is landed on a pilot `landed` or a loop `ticket_done`.

    Go quota is one shared weekly percentage, so per-ticket cost is the
    phases' own list-price figures.
    """
    spent: dict[str, list[float]] = defaultdict(lambda: [0.0, 0])
    landed, parked = set(), set()
    for event in events:
        ticket = ticket_of(event)
        if ticket is None:
            continue
        if event["kind"] in ("phase_end", "lane_cost"):
            spent[ticket][0] += float(event.get("cost") or 0)
            spent[ticket][1] += int(event.get("tokens") or 0)
        elif event["kind"] in ("landed", "ticket_done"):
            landed.add(ticket)
        elif event["kind"] == "ticket_parked":
            parked.add(ticket)
    out = {}
    for name, group in (("landed", landed), ("parked", parked - landed)):
        rows = [spent[t] for t in group if t in spent]
        out[name] = (len(group), round(sum(r[0] for r in rows), 4), int(sum(r[1] for r in rows)), len(rows))
    return out


def summarise(events: list[dict]) -> dict:
    rows = tickets(events)
    totals = attribute(rows, segments(events))
    total = sum(int(end) - int(start) for _, _, start, end in rows)
    live = activity(events)
    span = live[-1]["t"] - live[0]["t"] if len(live) > 1 else 0.0
    gates = [e for e in events if e["kind"] == "gate_done"]
    lane_gates = [e for e in events if e["kind"] == "gate_lane"]
    skipped = [e for e in lane_gates if cached(e)]
    preskipped = [e for e in events if e["kind"] == "gate_skipped"]
    wakes = Counter()
    for event in events:
        if event["kind"] == "wake":
            wakes[str(event.get("why") or event.get("reason") or "unknown")] += 1
    buckets: dict[int, list[dict]] = defaultdict(list)
    begin = events[0]["t"] if events else 0.0
    for event in events:
        if event["kind"] == "machine":
            buckets[int((event["t"] - begin) // 3600)].append(event)
    load = {}
    for hour, samples in buckets.items():
        loads = [float(s.get("load1") or 0) for s in samples]
        ram = [float(s.get("ram_free_mb") or 0) for s in samples]
        load[hour] = (sum(loads) / len(loads), max(loads), sum(ram) / len(ram))
    waits = sorted(((cat, totals[cat]) for cat in CATS
                    if cat not in ("LLM", "unexplained") and totals[cat] > 0),
                   key=lambda pair: pair[1], reverse=True)[:3]
    return {"tickets": len(rows), "total": total, "shares": totals, "span": span,
            "gates": len(gates), "skipped": len(skipped), "preskipped": len(preskipped),
            "saved": sum(float(e.get("seconds") or 0) for e in skipped),
            "wakes": wakes, "load": load, "waits": waits, "cost": ticket_costs(events)}


def table(head: list[str], rows: list[list]) -> str:
    body = [[str(cell) for cell in row] for row in rows]
    widths = [max([len(head[i])] + [len(row[i]) if i < len(row) else 0 for row in body])
              for i in range(len(head))]
    lines = ["  ".join(cell.ljust(widths[i]) for i, cell in enumerate(head)).rstrip()]
    for row in body:
        lines.append("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip())
    return "\n".join(lines)


def compact(tokens: float) -> str:
    return f"{tokens / 1e6:.1f}M" if tokens >= 1e6 else f"{tokens / 1e3:.1f}k"


def cost_block(names: list[str], summaries: list[dict]) -> str:
    if not any(c for s in summaries for _, c, _, _ in s["cost"].values()):
        return ""
    rows = []
    for outcome in ("landed", "parked"):
        stats = [s["cost"][outcome] for s in summaries]
        rows.append([f"{outcome} tickets"] + [f"{n} ({k} of {n} priced)" if k < n else str(n)
                                              for n, _, _, k in stats])
        rows.append([f"list $/{outcome} ticket"] + [f"${c / k:.2f}" if k else "-" for _, c, _, k in stats])
        rows.append([f"tokens/{outcome} ticket"] + [compact(t / k) if k else "-" for _, _, t, k in stats])
    return table([""] + names, rows)


def report(names: list[str], summaries: list[dict]) -> str:
    out = []
    rows = []
    rows.append(["tickets"] + [str(s["tickets"]) for s in summaries])
    rows.append(["hours"] + [f"{s['span'] / 3600:.1f}" for s in summaries])
    rows.append(["tickets/hour"] + [f"{s['tickets'] / max(s['span'] / 3600, 0.01):.1f}" for s in summaries])
    rows.append(["gates"] + [str(s["gates"]) for s in summaries])
    rows.append(["gates/ticket"] + [f"{s['gates'] / s['tickets']:.1f}" if s["tickets"] else "-" for s in summaries])
    rows.append(["cache skips"] + [str(s["skipped"]) for s in summaries])
    rows.append(["baseline skips"] + [str(s["preskipped"]) for s in summaries])
    rows.append(["seconds saved"] + [human(s["saved"]) for s in summaries])
    rows.append(["biggest waits"] + ["; ".join(f"{cat} {human(sec)}" for cat, sec in s["waits"]) or "-"
                                     for s in summaries])
    out.append(table([""] + names, rows))
    out.append("")
    if block := cost_block(names, summaries):
        out.extend([block, ""])
    rows = []
    for cat in CATS:
        cells = []
        for s in summaries:
            total = s["total"]
            cells.append(f"{s['shares'][cat] / total:.0%} ({human(s['shares'][cat])})" if total else "-")
        rows.append([cat] + cells)
    out.append(table(["ticket time"] + names, rows))
    out.append("")
    hours = sorted({hour for s in summaries for hour in s["load"]})
    if hours:
        rows = []
        for hour in hours:
            cells = []
            for s in summaries:
                if hour in s["load"]:
                    avg, peak, ram = s["load"][hour]
                    cells.append(f"load {avg:.1f}, peak {peak:.1f}, {ram / 1000:.0f}G free")
                else:
                    cells.append("-")
            rows.append([f"h{hour}"] + cells)
        out.append(table(["load by hour"] + names, rows))
        out.append("")
    reasons = sorted({reason for s in summaries for reason in s["wakes"]},
                     key=lambda r: -sum(s["wakes"][r] for s in summaries))
    if reasons:
        rows = [[reason] + [str(s["wakes"][reason]) if s["wakes"][reason] else "-" for s in summaries]
                for reason in reasons]
        out.append(table(["wakes"] + names, rows))
    return "\n".join(out).rstrip()


def main(argv: list[str]) -> int:
    if not argv:
        sys.exit("usage: run-report.py <run> [<run> ...]")
    names, summaries, missing = [], [], []
    for name in argv:
        path = find_log(name)
        if path is None:
            missing.append(name)
            continue
        names.append(name)
        summaries.append(summarise(read(path)))
    for name in missing:
        print(f"run-report.py: no log for {name} under {runlog.base_dir()}", file=sys.stderr)
    if not names:
        return 1
    print(report(names, summaries))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
