#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Tell an orchestrator which GitHub issues to work on next.

    next-tickets.py --queue four-player-playtest [--hold L] [--ready-label L] [--json]

Reads every issue (open and closed, since a "Depends on:" line may point out
of the queue) in the cwd's repo, then sorts the open queue tickets into
buckets: in flight, unreadied, ready, can start from a dependency's tip,
held, blocked. Unreadied is the one to read first: a ticket whose
dependencies are done but that nobody labelled sits unstarted for hours.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

BUCKETS = ["in_flight", "unreadied", "ready", "can_start", "held", "blocked"]
TITLES = {
    "in_flight": "IN FLIGHT",
    "unreadied": "UNREADIED (deps done, no ready label: read the body, add the label)",
    "ready": "READY",
    "can_start": "CAN START FROM A DEPENDENCY'S TIP",
    "held": "HELD",
    "blocked": "BLOCKED",
}
NO_PRIORITY = 9
PRIORITY_WORDS = {"priority:high": 1, "priority:low": 3}
DEPENDS = re.compile(r"depends on:?([^\n]*)", re.IGNORECASE)


def labels_of(issue: dict) -> list[str]:
    return [label["name"] for label in issue["labels"]]


def deps_of(issue: dict) -> list[int]:
    found: list[int] = []
    for line in DEPENDS.findall(issue.get("body") or ""):
        found += [int(n) for n in re.findall(r"#(\d+)", line)]
    return sorted(set(found))


def priority_of(labels: list[str]) -> int:
    best = NO_PRIORITY
    for name in labels:
        if name in PRIORITY_WORDS:
            best = min(best, PRIORITY_WORDS[name])
        elif m := re.fullmatch(r"priority:(\d+)", name):
            best = min(best, int(m[1]))
    return best


def stage_of(labels: list[str]) -> str | None:
    return next((n for n in labels if n.startswith("stage:")), None)


def unblock_counts(queue: dict[int, list[int]]) -> dict[int, int]:
    """Open queue tickets that wait on each ticket, directly or not."""
    dependents: dict[int, set[int]] = {n: set() for n in queue}
    for n, deps in queue.items():
        for d in deps:
            if d in dependents:
                dependents[d].add(n)

    def reach(n: int, seen: set[int]) -> set[int]:
        for m in dependents[n] - seen:
            seen.add(m)
            reach(m, seen)
        return seen

    return {n: len(reach(n, set())) for n in queue}


def classify(issues: list[dict], queue_labels: list[str], hold: list[str], ready_label: str) -> dict:
    by_num = {i["number"]: i for i in issues}
    queue = {
        i["number"]: deps_of(i)
        for i in issues
        if i["state"].upper() == "OPEN" and set(labels_of(i)) & set(queue_labels)
    }
    unblocks = unblock_counts(queue)
    out: dict[str, list[dict]] = {b: [] for b in BUCKETS}

    for num, deps in queue.items():
        issue = by_num[num]
        labels = labels_of(issue)
        stage = stage_of(labels)
        held_by = [h for h in hold if h in labels]
        open_deps = [d for d in deps if d in by_num and by_num[d]["state"].upper() == "OPEN"]
        dep_stage = {d: stage_of(labels_of(by_num[d])) for d in open_deps}
        sizes = [n for n in labels if n.startswith("size:")]
        row = {
            "number": num,
            "priority": priority_of(labels),
            "size": sizes[0] if sizes else "",
            "title": issue["title"],
            "unblocks": unblocks[num],
            "notes": [],
        }
        ready = ready_label in labels
        if stage:
            bucket = "in_flight"
            row["notes"].append(stage)
        elif held_by:
            bucket = "held"
            row["notes"].append("held by " + ", ".join(held_by))
        elif open_deps and all(dep_stage[d] == "stage:reviewing" for d in open_deps):
            bucket = "can_start"
            row["notes"] += [f"from #{d}'s tip" for d in open_deps]
            if not ready:
                row["notes"].append(f"no {ready_label}")
        elif open_deps:
            bucket = "blocked"
            row["notes"] += [f"#{d} {dep_stage[d] or 'open'}" for d in open_deps]
        else:
            bucket = "ready" if ready else "unreadied"
        if row["priority"] == NO_PRIORITY and bucket not in ("held", "in_flight"):
            row["notes"].append("NO PRIORITY LABEL")
        elif row["priority"] == NO_PRIORITY:
            row["notes"].append("no priority")
        if row["unblocks"] and bucket in ("ready", "unreadied", "can_start"):
            row["notes"].append(f"unblocks {row['unblocks']}")
        out[bucket].append(row)

    for rows in out.values():
        rows.sort(key=lambda r: (r["priority"], -r["unblocks"], r["number"]))
    return out


def render(buckets: dict) -> str:
    counts = ", ".join(f"{len(buckets[b])} {b.replace('_', ' ')}" for b in BUCKETS)
    lines = [counts]
    for b in BUCKETS:
        rows = buckets[b]
        if not rows:
            continue
        lines.append("")
        lines.append(f"== {TITLES[b]}: {len(rows)} ==")
        if b == "unreadied":
            lines.append("!! Nobody started these. Read each body, add the ready label if the spec is full.")
        for r in rows:
            prio = "P-" if r["priority"] == NO_PRIORITY else f"P{r['priority']}"
            title = r["title"] if len(r["title"]) <= 70 else r["title"][:69] + "…"
            note = "; ".join(r["notes"])
            lines.append(f"#{r['number']:<5} {prio:<3} {r['size'].removeprefix('size:'):<2} {title:<70}  {note}".rstrip())
    return "\n".join(lines)


def fetch(repo: str | None) -> list[dict]:
    cmd = ["gh", "issue", "list", "--state", "all", "--limit", "2000",
           "--json", "number,state,title,labels,body"]
    if repo:
        cmd += ["--repo", repo]
    done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode:
        sys.exit(f"next-tickets: gh failed: {done.stderr.strip()}")
    return json.loads(done.stdout)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--queue", action="append", required=True, help="label of the queue (repeatable)")
    ap.add_argument("--hold", action="append", help="label waiting on Greg (default needs-greg, manual)")
    ap.add_argument("--ready-label", default="ready-for-agent")
    ap.add_argument("--repo", help="owner/name, default the cwd's repo")
    ap.add_argument("--json", action="store_true", help="print the buckets as JSON")
    args = ap.parse_args()
    buckets = classify(fetch(args.repo), args.queue, args.hold or ["needs-greg", "manual"], args.ready_label)
    print(json.dumps(buckets, indent=2) if args.json else render(buckets))


if __name__ == "__main__":
    main()
