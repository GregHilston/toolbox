#!/usr/bin/env python3
"""Print where a swarm run's time went, from runlog.py's JSON lines.

    run-report.py <run> [<run> ...] [--since EPOCH] [--pilot DIR]
    run-report.py --log <lane log>

A single run also prints each ticket's minutes in every phase (slot or
dependency wait, worker, review, fix round, ready, landing, hold), its gate
runs by where they ran, and the waits ranked by minutes with a fix for each.
`--since` drops earlier events from a log shared with an older run, and
`--pilot` reads lane queue times from a pilot.log the pilot never logged.

Each ticket's time is split by intervals (its phase_start/phase_end, gates,
tests, landing), and whatever no interval covers is unexplained. "queue" is a
work gate's wait for a slot; "gate wait" is a landing gate's. A run's last
ticket extends to its lane's landing, so the landing is charged to it.
"review" is the review queue plus the review run. "Hours in no ticket" is each
lane's first-to-last event span, summed over worker lanes, minus the summed
ticket time (never below zero), so dropped seconds stay visible. An untagged
ticket_parked closes nothing.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runlog
import steptime

CATS = ["queue", "parked", "prep", "LLM", "own tests", "gate wait", "gate run", "review", "fix", "ready wait",
        "landing", "unexplained"]
# Measured activity outranks the labels for waiting between steps.
PRIORITY = {"prep": 1, "parked": 1, "ready wait": 1, "LLM": 2, "fix": 3, "review": 4, "landing": 5, "queue": 6,
            "gate wait": 7, "gate run": 8, "own tests": 9}
LIFE = {"ticket_parked": "parked", "prep_start": "prep", "review_start": "review", "fix_start": "fix",
        "ready": "ready wait", "land_start": None}
AFTER_LANE = set(LIFE) | {"land_done", "land_batch", "landed"}
WAKE_KEYS = ["CONFLICT", "produced no commits", "parked", "did not land", "removes more assertions",
             "ALL SETTLED", "waits:", "fix \\d+", "died", "stopped"]
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


def owned(events: list[dict]) -> list[tuple[dict, str | None]]:
    """Pair each event with its ticket; an untagged one after a lane's stop takes that stopped ticket.

    So prep is the stopped ticket's wait before review, counted against it.
    An untagged event once a later ticket has started has no owner and is
    dropped, so its time stays unexplained or falls in "hours in no ticket".

    A lane's stopped ticket clears at its next ticket_start, so an untagged
    event can never land on a ticket that began after it.
    """
    current: dict[str, str | None] = {}
    stopped: dict[str, str | None] = {}
    out: list[tuple[dict, str | None]] = []
    for event in events:
        lane, kind, ticket = lane_of(event), event["kind"], ticket_of(event)
        if kind == "ticket_start":
            current[lane] = ticket
            stopped.pop(lane, None)
        elif kind == "ticket_done" or (kind == "ticket_parked" and ticket):
            stopped[lane] = ticket or current.get(lane)
            current.pop(lane, None)
        elif ticket is None and kind in AFTER_LANE and kind != "ticket_parked":
            ticket = stopped.get(lane)
        out.append((event, ticket))
    return out


def tickets(events: list[dict]) -> list[list]:
    """One [lane, ticket, start, end] per ticket_start, extended to the lane's landing."""
    rows: list[list] = []
    opened: dict[str, tuple[str | None, float]] = {}
    parked: dict[tuple[str, str | None], float] = {}
    lane_end: dict[str, float] = {}
    for event in events:
        lane = lane_of(event)
        if event["kind"] == "ticket_start":
            if lane in opened:
                ticket, start = opened.pop(lane)
                rows.append([lane, ticket, start, event["t"]])
                lane_end[lane] = event["t"]
            ticket = ticket_of(event)
            opened[lane] = (ticket, max(parked.pop((lane, ticket), event["t"]), lane_end.get(lane, 0.0)))
        elif event["kind"] in ("ticket_done", "ticket_parked") and lane in opened:
            if ticket_of(event) not in (None, opened[lane][0]) or (event["kind"] == "ticket_parked"
                                                                    and not ticket_of(event)):
                continue
            ticket, start = opened.pop(lane)
            rows.append([lane, ticket, start, event["t"]])
            lane_end[lane] = event["t"]
            if event["kind"] == "ticket_parked":
                parked[(lane, ticket)] = event["t"]
    finish = activity(events)[-1]["t"] if events else 0.0
    for lane, (ticket, start) in opened.items():
        rows.append([lane, ticket, start, finish])
    rows.sort(key=lambda row: row[2])
    if not rows:
        return rows
    for event, ticket in owned(events):
        if event["kind"] in AFTER_LANE and ticket:
            mine = [row for row in rows if row[0] == lane_of(event) and row[1] == ticket
                    and row[2] <= event["t"]]
            if mine:
                mine[-1][3] = max(mine[-1][3], event["t"])
    return rows


def segments(events: list[dict]) -> list[tuple[float, float, str, str, str | None]]:
    """(start, end, category, lane, ticket) for every paired interval."""
    out: list[tuple[float, float, str, str, str | None]] = []
    phases: dict[tuple, float] = {}
    queued: dict[str, tuple[float, str | None]] = {}
    running: dict[str, float] = {}
    lands: dict[str, tuple[float, str | None]] = {}
    marks: dict[tuple, tuple[float, str | None]] = {}
    for event, ticket in owned(events):
        lane, kind = lane_of(event), event["kind"]
        if kind == "ticket_start":
            for key in [key for key in marks if key[0] == lane]:
                begin, cat = marks.pop(key)
                if cat:
                    out.append((begin, event["t"], cat, lane, key[1]))
        if kind in LIFE and ticket:
            before = marks.get((lane, ticket))
            if before and before[1]:
                out.append((before[0], event["t"], before[1], lane, ticket))
            marks[(lane, ticket)] = (event["t"], LIFE[kind])
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
            lands[lane] = (event["t"], ticket)
        elif kind == "land_done" and lane in lands:
            begin, owner = lands.pop(lane)
            if owner:
                out.append((begin, event["t"], "landing", lane, owner))
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


def wake_reason(text: str) -> str:
    """Group free-text attention lines by their cause, not their lane."""
    for key in WAKE_KEYS:
        if re.search(key, text):
            return key.replace("\\d+", "N")
    return text[:40]


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
    workers = {lane_of(e) for e in live if e["kind"] == "lane_start"}
    lane_times: dict[str, list[float]] = defaultdict(list)
    for event in live:
        if lane_of(event) in workers:
            lane_times[lane_of(event)].append(event["t"])
    lane_hours = sum(max(times) - min(times) for times in lane_times.values())
    gates = [e for e in events if e["kind"] == "gate_done"]
    lane_gates = [e for e in events if e["kind"] == "gate_lane"]
    skipped = [e for e in lane_gates if cached(e)]
    preskipped = [e for e in events if e["kind"] == "gate_skipped"]
    wakes = Counter()
    for event in events:
        if event["kind"] == "wake":
            wakes[wake_reason(str(event.get("why") or event.get("reason") or "unknown"))] += 1
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
            "no_ticket": max(lane_hours - total, 0.0) if workers else None, "wakes": wakes, "load": load, "waits": waits,
            "other": other_top(events), "cost": ticket_costs(events)}


def other_top(events: list[dict]) -> str:
    """The commands that most often hold `other` CPU, from the machine samples."""
    sums: Counter = Counter()
    for event in events:
        if event["kind"] == "machine":
            sums.update(event.get("other_top") or {})
    return ", ".join(name for name, _ in sums.most_common(3))


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
    rows.append(["ticket hours (summed)"] + [f"{s['total'] / 3600:.1f}" for s in summaries])
    rows.append(["hours unexplained"] + [f"{s['shares']['unexplained'] / 3600:.1f}" for s in summaries])
    rows.append(["hours in no ticket"] + [f"{s['no_ticket'] / 3600:.1f}" if s["no_ticket"] is not None else "-"
                                          for s in summaries])
    rows.append(["run span unexplained"] + [f"{s['shares']['unexplained'] / s['span']:.0%}" if s["span"] else "-"
                                              for s in summaries])
    rows.append(["top other CPU (summed)"] + [s["other"] or "-" for s in summaries])
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


PHASES = ["dep", "wait", "worker", "review", "fix", "ready", "landing", "hold"]
PHASE_LABEL = {"dep": "dependency wait", "wait": "slot wait", "worker": "worker", "review": "review", "fix": "fix round",
               "ready": "ready->landing", "landing": "landing", "hold": "hold (orchestrator)"}
FIXES = {
    "dep": "an `after` line held the lane behind another ticket: drop it unless the files truly overlap",
    "wait": "the lane cap held a queued lane: raise `pilot/start`",
    "worker": "worker time itself: see the worker-time block for LLM, test, sweep and gate minutes",
    "review": "review run plus the pilot's poll before it: start review at once, shorten the poll",
    "fix": "fix rounds: have the reviewer's decisions arrive with the first hold, not after a second pass",
    "ready": "a ready ticket waits for the pilot loop to batch it: land on `ready`, not on the next poll",
    "landing": "the landing gate: skip the gate when the tree already passed, batch more tickets per gate",
    "hold": "a ticket sat in hold for the orchestrator: fix what parked it (red landing gate, conflict, stray file)",
}
TRANSITIONS = {"lane_queued": "wait", "lane_start": "worker", "ticket_done": "review", "ticket_parked": "review",
               "prep_start": "review", "review_start": "review", "fix_start": "fix", "ready": "ready",
               "land_start": "landing"}


def lane_ticket_map(events: list[dict]) -> dict[str, str]:
    """Each lane's ticket, from its ticket_start or any tagged lane event."""
    out: dict[str, str] = {}
    for event in events:
        lane, ticket = lane_of(event), ticket_of(event)
        if lane and ticket and event["kind"] != "machine":
            out.setdefault(lane, ticket)
    return out


def worktree_tickets(events: list[dict], lanes: dict[str, str]) -> dict[str, set[str]]:
    """Worktree folder name -> tickets it served: a lane clone, or a landing batch."""
    out: dict[str, set[str]] = defaultdict(set)
    for event in events:
        if event["kind"] == "land_start" and event.get("batch") and ticket_of(event):
            out[str(event["batch"])].add(ticket_of(event) or "")
    return out


def gate_ticket(worktree: str, by_name: dict[str, set[str]], lanes: dict[str, str]) -> tuple[str, set[str]]:
    """(where the gate ran, tickets it served): lane clone, prep/landing worktree, or the main checkout."""
    name = Path(worktree).name
    if "worktrees" not in worktree and name.startswith("gridkeep-") and name[9:] in lanes:
        return "lane", {lanes[name[9:]]}
    if name in by_name:
        return "prep", set(by_name[name])
    found = re.match(r"l-(.+)-\w+$", name)
    if found and found.group(1) in lanes:
        return "prep", {lanes[found.group(1)]}
    return "hand", set()


def lifecycle(events: list[dict]) -> dict[str, dict]:
    """Per ticket: seconds in each phase between queued and landed, plus its gates.

    The phase is the last state transition: queued, worker, review, fix round,
    ready, landing, or hold after a failed landing or a `lane_state hold`. A
    ticket with no `landed` event runs to its last event and is not counted done.
    """
    lanes = lane_ticket_map(events)
    by_name = worktree_tickets(events, lanes)
    moves: dict[str, list[tuple[float, str]]] = defaultdict(list)
    landed: dict[str, float] = {}
    after: dict[str, str] = {}
    for event in events:
        kind, lane = event["kind"], lane_of(event)
        ticket = ticket_of(event) or lanes.get(lane)
        if not ticket or kind == "machine":
            continue
        if kind == "lane_queued" and event.get("after") in lanes:
            after[ticket] = lanes[event["after"]]
        if kind in TRANSITIONS:
            moves[ticket].append((event["t"], TRANSITIONS[kind]))
        elif kind == "lane_state" and event.get("state") == "hold":
            moves[ticket].append((event["t"], "hold"))
        elif kind == "land_done" and event.get("ok") is False:
            moves[ticket].append((event["t"], "hold"))
        elif kind == "landed" and event.get("ok") is not False:
            landed.setdefault(ticket, event["t"])
    out: dict[str, dict] = {}
    for ticket, seq in moves.items():
        end = landed.get(ticket)
        stop = end if end is not None else max(t for t, _ in seq)
        spent: Counter = Counter()
        segs: list[tuple[float, float, str]] = []
        for (begin, phase), (later, _) in zip(seq, seq[1:] + [(stop, "")]):
            begin, later = min(begin, stop), min(later, stop)
            if phase == "wait" and after.get(ticket) in landed and landed[after[ticket]] > begin:
                cut = min(landed[after[ticket]], later)
                segs.append((begin, cut, "dep"))
                begin = cut
                phase = "wait"
            segs.append((begin, later, phase))
        for begin, later, phase in segs:
            spent[phase] += max(0.0, later - begin)
        out[ticket] = {"segs": segs, "lane": next((ln for ln, t in lanes.items() if t == ticket), "?"), "start": seq[0][0],
                       "end": end, "spent": spent, "gates": Counter(), "gate_s": 0.0, "dup_s": 0.0,
                       "dup": 0, "wait_s": 0.0}
    seen: Counter = Counter()
    last_gate: dict[str, tuple[float, int | None]] = {}
    landings = [e["t"] for e in events if e["kind"] == "landed"]
    for event in events:
        kind = event["kind"]
        if kind not in ("gate_done", "gate_slot"):
            continue
        where, tickets_ = gate_ticket(str(event.get("worktree", "")), by_name, lanes)
        mine = [t for t in tickets_ if t in out]
        if kind == "gate_slot":
            for ticket in mine:
                out[ticket]["wait_s"] += float(event.get("wait") or 0) / len(mine)
            continue
        gate = str(event.get("gate_kind") or "worker")
        label = "baseline" if gate == "baseline" else "landing" if gate == "landing" else (
            "worker" if where == "lane" else "check" if where == "prep" else "hand")
        if event.get("full") is False:
            label = "partial"
        seconds = float(event.get("seconds") or 0)
        for ticket in mine:
            row = out[ticket]
            row["gates"][label] += 1 / len(mine)
            row["gate_s"] += seconds / len(mine)
            tree = event.get("tree")
            if tree and label != "partial":
                seen[(ticket, tree)] += 1
                same = seen[(ticket, tree)] > 1
            else:
                # Without a logged tree: a gate within 150 s of the last one in its worktree, main unmoved.
                before = last_gate.get(str(event.get("worktree")))
                start = event["t"] - seconds
                same = bool(before and 0 <= start - before[0] < 150 and len(mine) == 1
                            and not any(before[0] < moved < start for moved in landings))
            if same and label != "partial":
                row["dup"] += 1
                row["dup_s"] += seconds / len(mine)
        last_gate[str(event.get("worktree"))] = (event["t"], event.get("exit"))
    return out


def concurrency(rows: dict[str, dict]) -> str:
    """Tickets being worked, reviewed, fixed or landed at once, and the minutes nothing was."""
    active = {"worker", "review", "fix", "ready", "landing"}
    marks = sorted((b, e) for r in rows.values() for b, e, p in r["segs"] if p in active and e > b)
    if not marks:
        return ""
    low = min(b for b, _ in marks)
    high = max(r["end"] for r in rows.values() if r["end"]) if any(r["end"] for r in rows.values()) else marks[-1][1]
    count: Counter = Counter()
    for b, e in marks:
        for minute in range(int((b - low) // 60), int((min(e, high) - low) // 60)):
            count[minute] += 1
    span = int((high - low) // 60)
    idle, thin = sum(1 for m in range(span) if count[m] == 0), sum(1 for m in range(span) if 0 < count[m] <= 2)
    return (f"in flight (worker, review, fix, ready or landing): average {sum(count.values()) / max(span, 1):.1f} "
            f"tickets over {span} min; none for {idle} min, one or two for {thin} min")


def phase_table(rows: dict[str, dict]) -> str:
    """One row per landed ticket (minutes), then totals and medians, then tickets that never landed."""
    def mins(value: float) -> str:
        return f"{value / 60:.0f}"
    done = {t: r for t, r in rows.items() if r["end"] is not None}
    head = ["ticket", "lane", "wall", *PHASES, "gates", "gate min"]
    body = []
    for ticket, row in sorted(done.items(), key=lambda kv: kv[1]["end"]):
        wall = row["end"] - row["start"]
        gates = sum(row["gates"].values())
        body.append([f"#{ticket}", row["lane"][:18], mins(wall), *(mins(row["spent"][p]) for p in PHASES),
                     f"{gates:.0f}", mins(row["gate_s"])])
    if done:
        cols = [[r["end"] - r["start"] for r in done.values()]] + [[r["spent"][p] for r in done.values()]
                                                                  for p in PHASES]
        body.append(["total", "", *(mins(sum(c)) for c in cols),
                     f"{sum(sum(r['gates'].values()) for r in done.values()):.0f}",
                     mins(sum(r["gate_s"] for r in done.values()))])
        body.append(["median", "", *(mins(sorted(c)[len(c) // 2]) for c in cols), "", ""])
    out = [f"minutes in each phase, {len(done)} tickets done", table(head, body)]
    unlanded = [f"#{t} ({r['lane']})" for t, r in rows.items() if r["end"] is None]
    if unlanded:
        out.append("not landed: " + ", ".join(unlanded))
    return "\n".join(out)


def gate_table(rows: dict[str, dict]) -> str:
    """Gate runs and minutes per ticket by where they ran, and the second runs on an identical tree."""
    kinds = ["baseline", "worker", "check", "landing", "hand", "partial"]
    body = []
    for ticket, row in sorted(rows.items(), key=lambda kv: kv[1]["start"]):
        if not sum(row["gates"].values()):
            continue
        body.append([f"#{ticket}", *(f"{row['gates'][k]:.0f}" if row["gates"][k] else "-" for k in kinds),
                     f"{row['gate_s'] / 60:.0f}", f"{row['wait_s'] / 60:.1f}",
                     f"{row['dup']} ({row['dup_s'] / 60:.0f}m)" if row["dup"] else "-"])
    total = [sum(r["gates"][k] for r in rows.values()) for k in kinds]
    body.append(["total", *(f"{n:.0f}" for n in total), f"{sum(r['gate_s'] for r in rows.values()) / 60:.0f}",
                 f"{sum(r['wait_s'] for r in rows.values()) / 60:.1f}",
                 f"{sum(r['dup'] for r in rows.values())} ({sum(r['dup_s'] for r in rows.values()) / 60:.0f}m)"])
    return "\n".join(["gate runs per ticket (worker = in the lane, check = fix round or review worktree, "
                       "hand = main checkout or unmapped)",
                       table(["ticket", *kinds, "gate min", "slot wait min", "same-tree reruns"], body)])


def ranked_waits(rows: dict[str, dict], top: int = 8, hung: list[str] | None = None) -> str:
    """The phases other than worker time, ranked by total minutes, each with where it hit and a fix."""
    totals: list[tuple[float, str, str]] = []
    for phase in PHASES:
        if phase == "worker":
            continue
        ranked = sorted(((r["spent"][phase], t) for t, r in rows.items() if r["spent"][phase] > 0), reverse=True)
        total = sum(sec for sec, _ in ranked)
        if total:
            where = ", ".join(f"#{t} {sec / 60:.0f}m" for sec, t in ranked[:3])
            totals.append((total, PHASE_LABEL[phase], f"{where}; {FIXES[phase]}"))
    dup = sum(r["dup_s"] for r in rows.values())
    if dup:
        totals.append((dup, "same-tree gate reruns", "a gate on a tree that already ran: skip it"))
    for line in hung or []:
        cmd, _, minutes = line.removeprefix("hung: ").rpartition("m (")[0].rpartition(" ")
        totals.append((float(minutes) * 60, "hung", f"{cmd}; a tool timeout killed it: fix what it waits on"))
    totals.sort(reverse=True)
    body = [[str(i + 1), f"{sec / 60:.0f}", name, why] for i, (sec, name, why) in enumerate(totals[:top])]
    return "\n".join(["biggest waits, ticket-minutes (tickets overlap, so these exceed wall time)",
                       table(["#", "min", "wait", "where and fix"], body)])


def unattributed_gates(events: list[dict]) -> str:
    """Gates that served no ticket: reruns by hand in the main checkout, or a one-off fix worktree."""
    lanes = lane_ticket_map(events)
    by_name = worktree_tickets(events, lanes)
    gates = [e for e in events if e["kind"] == "gate_done"
             and not gate_ticket(str(e.get("worktree", "")), by_name, lanes)[1]]
    if not gates:
        return ""
    seconds = sum(float(e.get("seconds") or 0) for e in gates)
    return f"gates serving no ticket (hand reruns, fix worktrees): {len(gates)} runs, {seconds / 60:.0f} min"


def lifecycle_report(events: list[dict]) -> str:
    rows = lifecycle(events)
    if not rows:
        return ""
    return "\n\n".join(part for part in [phase_table(rows), concurrency(rows), gate_table(rows),
                                         unattributed_gates(events),
                                         ranked_waits(rows, hung=hung_lines(worker_steps(events)))] if part)


def pilot_log_events(path: Path, day: float) -> list[dict]:
    """Events for a run whose pilot never logged them, from pilot.log's `HH:MM:SS` lines on `day`'s date."""
    import datetime
    base = datetime.datetime.fromtimestamp(day).replace(hour=0, minute=0, second=0, microsecond=0)
    out = []
    after: dict[str, str] = {}
    queue = path.with_name("queue")
    if queue.exists():
        for line in queue.read_text(errors="replace").splitlines():
            words = line.split()
            if len(words) >= 3 and words[1] == "after":
                after[words[0]] = words[2]
            elif len(words) >= 4 and words[2] == "after":
                after[words[0]] = words[3]
    lines = path.read_text(errors="replace").splitlines()
    for line in lines:
        if waits := re.search(r"ATTENTION (\S+) waits: (\S+) is", line):
            after.setdefault(waits.group(1), waits.group(2))
    for line in lines:
        found = re.match(r"(\d\d):(\d\d):(\d\d) (.*)", line)
        if not found:
            continue
        h, m, sec, rest = found.groups()
        t = (base + datetime.timedelta(hours=int(h), minutes=int(m), seconds=int(sec))).timestamp()
        if queued := re.match(r"added (\S+) from queue", rest):
            out.append({"kind": "lane_queued", "lane": queued.group(1), "t": t,
                        **({"after": after[queued.group(1)]} if queued.group(1) in after else {})})
        elif held := re.match(r"(\S+) -> hold$", rest):
            out.append({"kind": "lane_state", "lane": held.group(1), "state": "hold", "t": t})
    return out


WORKER_CATS = ["LLM thinking", "test runs", "gates", "sweeps", "other commands"]


def worker_steps(events: list[dict]) -> dict[str, list[dict]]:
    """Each ticket's (or lane's) timed worker steps, as steptime's lines."""
    out: dict[str, list[dict]] = defaultdict(list)
    for event in events:
        if event["kind"] not in ("llm_turn", "worker_cmd"):
            continue
        key = ticket_of(event) or lane_of(event) or "?"
        seconds = float(event.get("seconds") or 0)
        if event["kind"] == "llm_turn":
            out[key].append({"step": "llm", "seconds": seconds})
        else:
            out[key].append({"step": "cmd", "seconds": seconds, "cmd": str(event.get("cmd", "")),
                             "cat": str(event.get("cat") or steptime.categorise(str(event.get("cmd", ""))))}
                       | ({"hung": True} if event.get("hung") else {}))
    return out


def hung_lines(by_ticket: dict[str, list[dict]]) -> list[str]:
    """One `hung: <command> <minutes>` line per command a tool timeout killed."""
    return [f"hung: {s['cmd'][:100]!r} {s['seconds'] / 60:.0f}m ({'#' + k if k.isdigit() else k})"
            for k, found in sorted(by_ticket.items()) for s in found if s.get("hung")]


def worker_block(by_ticket: dict[str, list[dict]]) -> str:
    """Worker time by category per ticket, then each ticket's five slowest commands."""
    if not by_ticket:
        return ""
    rows, tops = [], []
    for key, found in sorted(by_ticket.items()):
        spent = Counter()
        for step in found:
            spent["LLM thinking" if step["step"] == "llm" else step["cat"]] += step["seconds"]
        total = sum(spent.values())
        rows.append([f"#{key}" if key.isdigit() else key, human(total)]
                    + [f"{spent[c] / total:.0%} ({human(spent[c])})" if total else "-" for c in WORKER_CATS])
        slow = sorted((s for s in found if s["step"] == "cmd"), key=lambda s: -s["seconds"])[:5]
        tops.append(f"top commands, {rows[-1][0]}:")
        tops.extend(f"  {human(s['seconds']):>5}  {s['cmd'][:100]!r}" for s in slow)
    return "\n".join([table(["worker time", "total"] + WORKER_CATS, rows), "", *hung_lines(by_ticket), *tops])


def log_events(path: Path) -> list[dict]:
    """A lane log's steps as run-log events, from step lines or an older raw pi stream."""
    return log_events_text(path.read_text(errors="replace"), path.stem)


def log_events_text(text: str, ticket: str) -> list[dict]:
    """log_events for a log already read."""
    return [{"kind": "llm_turn" if s["step"] == "llm" else "worker_cmd", "ticket": ticket, **s}
            for s in steptime.steps(text)]


def option(argv: list[str], name: str) -> str | None:
    """Pop `name VALUE` out of argv."""
    if name not in argv:
        return None
    at = argv.index(name)
    value = argv[at + 1] if at + 1 < len(argv) else ""
    del argv[at:at + 2]
    return value


def main(argv: list[str]) -> int:
    pilot, since = option(argv, "--pilot"), option(argv, "--since")
    if not argv:
        sys.exit("usage: run-report.py <run> [<run> ...] [--since EPOCH] [--pilot DIR] | run-report.py --log <lane log>")
    if argv[0] == "--log":
        block = worker_block(worker_steps(log_events(Path(argv[1]))))
        print(block or f"run-report.py: no timed steps in {argv[1]}")
        return 0 if block else 1
    names, summaries, missing, extra = [], [], [], []
    for name in argv:
        path = find_log(name)
        if path is None:
            missing.append(name)
            continue
        events = read(path)
        if since:
            events = [e for e in events if e["t"] >= float(since)]
        if pilot and not any(e["kind"] == "lane_queued" for e in events) and events:
            events = sorted(events + pilot_log_events(Path(pilot) / "pilot.log", events[-1]["t"]),
                            key=lambda e: e["t"])
        names.append(name)
        summaries.append(summarise(events))
        extra.append(lifecycle_report(events))
    for name in missing:
        now = runlog.current()
        hint = (f"; this repo's current run is {now!r}, and events land there until something runs "
                f"`runlog.py start {name}`") if now and now != name else ""
        print(f"run-report.py: no log for {name} under {runlog.base_dir()}{hint}", file=sys.stderr)
    if not names:
        return 1
    print(report(names, summaries))
    for name, block in zip(names, extra):
        if block:
            print(f"\n{name}\n{block}")
    for name, path in zip(names, map(find_log, names)):
        if block := worker_block(worker_steps(read(path))):
            print(f"\n{name} worker time\n{block}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
