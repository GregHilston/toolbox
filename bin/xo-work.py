#!/usr/bin/env python3
"""xo-work.py --repo OWNER/NAME --state FILE [--cap N] [--fixture FILE]

Prints an XO alert line for work that sits still while the CAG looks busy:
a ticket approved but not landed for 30 min, and free builder slots beside a
ready P0 for 20 min. The XO (control-loop.sh) runs it each pass and alerts
once an hour per line. Both slipped past every pane-based check on 2026-11-20.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

APPROVED_AFTER = 1800
SLOTS_AFTER = 1200
BUSY = {"stage:building", "stage:fixing"}
NOT_READY = {"needs-greg", "attended", "manual"}
DEPS = re.compile(r"^\s*(?:blocked by|depends on)\b(.*)$", re.I | re.M)


def labels(issue: dict) -> set[str]:
    return {lab["name"] for lab in issue.get("labels", [])}


def approved(issue: dict) -> bool:
    names = labels(issue)
    if "stage:approved" in names:
        return True
    comments = issue.get("comments") or []
    # Drains record a verdict only in a comment until lp #388 sets the label.
    return "stage:reviewing" in names and bool(comments) and "APPROVED" in comments[-1].get("body", "")


def blocked(issue: dict, open_numbers: set[int]) -> bool:
    for line in DEPS.findall(issue.get("body") or ""):
        if any(int(n) in open_numbers for n in re.findall(r"#(\d+)", line)):
            return True
    return False


def ready_p0(issues: list[dict]) -> list[int]:
    open_numbers = {i["number"] for i in issues}
    out = []
    for i in issues:
        names = labels(i)
        if "priority:0" not in names or "ready-for-agent" not in names:
            continue
        if any(n.startswith("stage:") for n in names) or names & NOT_READY or blocked(i, open_numbers):
            continue
        out.append(i["number"])
    return sorted(out)


def check(issues: list[dict], state: dict, now: float, cap: int, repo: str) -> tuple[list[str], dict]:
    alerts, seen = [], {}
    for i in issues:
        if approved(i):
            key = f"approved-{i['number']}"
            seen[key] = state.get(key, now)
            if now - seen[key] >= APPROVED_AFTER:
                alerts.append(f"XO {repo}: #{i['number']} approved over 30 min, not landed")
    busy = sum(1 for i in issues if labels(i) & BUSY)
    ready = ready_p0(issues)
    if busy < cap and ready:
        seen["slots"] = state.get("slots", now)
        if now - seen["slots"] >= SLOTS_AFTER:
            nums = " ".join(f"#{n}" for n in ready)
            alerts.append(f"XO {repo}: {cap - busy} of {cap} slots free beside ready P0s {nums} for 20 min")
    return alerts, seen


def fetch(slug: str) -> list[dict]:
    def gh(*args: str) -> list[dict]:
        return json.loads(subprocess.run(["gh", "issue", "list", "-R", slug, "--state", "open", *args],
                                         check=True, capture_output=True, text=True, timeout=60).stdout)
    issues = gh("--limit", "300", "--json", "number,labels,body")
    comments = {i["number"]: i["comments"] for i in gh("--label", "stage:reviewing", "--json", "number,comments")}
    for i in issues:
        i["comments"] = comments.get(i["number"], [])
    return issues


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--state", required=True, type=Path)
    p.add_argument("--cap", type=int, default=6)
    p.add_argument("--fixture", type=Path)
    a = p.parse_args()
    issues = json.loads(a.fixture.read_text()) if a.fixture else fetch(a.repo)
    try:
        state = json.loads(a.state.read_text())
    except (OSError, ValueError):
        state = {}
    alerts, seen = check(issues, state, time.time(), a.cap, a.repo.split("/")[-1])
    a.state.write_text(json.dumps(seen))
    print("\n".join(alerts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
