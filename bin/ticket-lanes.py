#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Swimlane time per `stage:*` label on GitHub issues, and drift alerts.

    ticket-lanes.py report --repo loser-picks [--since 2026-11-13] [--open] [--csv out.csv]
    ticket-lanes.py drift  --repo loser-picks [--pct 50] [--min-minutes 15]

Reads each issue's timeline: a stage interval runs from `labeled` to
`unlabeled`, else to close, else to now. "unlabeled" is the gap from the last
stage label's removal to close. Per-ticket time sums across fix rounds.
`drift` prints only when sure (min 5 tickets per window), exits 1 if it did,
and 2 on a fetch failure.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

OWNER = "GregHilston"
GAP = "unlabeled"
MIN_SAMPLE = 5


def parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def ticket_stats(events, closed, now):
    """Return {stage: (seconds, entries)} for one ticket."""
    end_of_time = closed or now
    opened, spans = {}, []
    for e in sorted(events, key=lambda e: e["created_at"]):
        name = (e.get("label") or {}).get("name", "")
        if not name.startswith("stage:"):
            continue
        t = parse(e["created_at"])
        if e["event"] == "labeled":
            opened.setdefault(name, t)
        elif e["event"] == "unlabeled" and name in opened:
            spans.append((name, opened.pop(name), t))
    spans += [(n, s, end_of_time) for n, s in opened.items()]
    out = {}
    for name, s, e in spans:
        sec, n = out.get(name, (0, 0))
        out[name] = (sec + max(0, int((e - s).total_seconds())), n + 1)
    if closed and spans and not opened:
        last = max(e for _, _, e in spans)
        if closed > last:
            out[GAP] = (int((closed - last).total_seconds()), 1)
    return out


def drift_lines(rows, now, pct=50, min_minutes=15):
    """rows: dicts with closed_at (datetime) and stats."""
    recent, prior = defaultdict(list), defaultdict(list)
    for r in rows:
        age = now - r["closed_at"]
        bucket = recent if age <= timedelta(days=7) else prior if age <= timedelta(days=28) else None
        if bucket is None:
            continue
        for stage, (sec, _) in r["stats"].items():
            bucket[stage].append(sec)
    lines = []
    for stage in sorted(recent):
        a, b = recent[stage], prior.get(stage, [])
        if len(a) < MIN_SAMPLE or len(b) < MIN_SAMPLE:
            continue
        ma, mb = statistics.median(a) / 60, statistics.median(b) / 60
        if ma - mb >= min_minutes and ma > mb * (1 + pct / 100):
            lines.append(f"{stage}: median {ma:.0f} min last 7d vs {mb:.0f} min prior 21d "
                         f"(+{(ma / mb - 1) * 100:.0f}%, n={len(a)}/{len(b)})")
    return lines


def gh(*args):
    for attempt in range(4):
        r = subprocess.run(["gh", *args], capture_output=True, text=True)
        if not r.returncode:
            return r.stdout
        time.sleep(1 + attempt)
    print(f"gh {' '.join(args[:3])}: {r.stderr.strip()}", file=sys.stderr)
    sys.exit(2)  # 1 is reserved for drift found


def fetch(repo, since, include_open, now):
    slug = f"{OWNER}/{repo}"
    issues = json.loads(gh("issue", "list", "-R", slug, "--state", "all", "--limit", "2000",
                           "--json", "number,state,closedAt,createdAt"))
    keep = []
    for i in issues:
        if i["closedAt"]:
            if parse(i["closedAt"]) >= since:
                keep.append(i)
        elif include_open and parse(i["createdAt"]) >= since - timedelta(days=60):
            keep.append(i)

    def one(i):
        raw = json.loads(gh("api", f"repos/{slug}/issues/{i['number']}/timeline",
                            "--paginate", "--slurp"))
        events = [e for page in raw for e in page if e.get("event") in ("labeled", "unlabeled")]
        closed = parse(i["closedAt"]) if i["closedAt"] else None
        return {"number": i["number"], "closed_at": closed,
                "stats": ticket_stats(events, closed, now), "events": events}

    with ThreadPoolExecutor(8) as ex:
        return list(ex.map(one, keep))


def pstat(vals):
    vals = sorted(vals)
    p90 = vals[min(len(vals) - 1, int(0.9 * len(vals)))]
    return len(vals), statistics.median(vals) / 60, p90 / 60, sum(vals) / 3600


def table(title, rows, now):
    per = defaultdict(list)
    entries = defaultdict(int)
    for r in rows:
        for stage, (sec, n) in r["stats"].items():
            per[stage].append(sec)
            entries[stage] += n
    print(f"\n{title}")
    print(f"  {'stage':<18}{'tickets':>8}{'entries':>8}{'median m':>10}{'p90 m':>8}{'total h':>9}")
    for stage in sorted(per):
        n, med, p90, tot = pstat(per[stage])
        print(f"  {stage:<18}{n:>8}{entries[stage]:>8}{med:>10.1f}{p90:>8.1f}{tot:>9.1f}")
    return per


def oddities(rows):
    overlap = left_on = 0
    for r in rows:
        on, over = set(), False
        for e in sorted(r["events"], key=lambda e: (e["created_at"], e["event"] == "labeled")):
            n = (e.get("label") or {}).get("name", "")
            if not n.startswith("stage:"):
                continue
            if e["event"] == "labeled":
                on.add(n)
                over = over or len(on) > 1
            else:
                on.discard(n)
        overlap += over
        left_on += bool(r["closed_at"] and on)
    print(f"\nodd: {overlap} tickets with overlapping stage labels; "
          f"{left_on} closed with a stage label still on")


def cmd_report(a, now):
    since = datetime.fromisoformat(a.since).replace(tzinfo=timezone.utc)
    rows = fetch(a.repo, since, a.open, now)
    table(f"{a.repo} since {a.since}: {len(rows)} tickets", rows, now)
    weeks = defaultdict(list)
    for r in rows:
        y, w, _ = (r["closed_at"] or now).isocalendar()
        weeks[(y, w)].append(r)
    for (y, w), rs in sorted(weeks.items()):
        table(f"ISO week {y}-W{w:02d} ({len(rs)} tickets)", rs, now)
    oddities(rows)
    if a.csv:
        with open(a.csv, "w", newline="") as f:
            wr = csv.writer(f)
            wr.writerow(["number", "closed_at", "stage", "seconds", "entries"])
            for r in rows:
                for stage, (sec, n) in sorted(r["stats"].items()):
                    wr.writerow([r["number"], r["closed_at"] or "", stage, sec, n])


def cmd_drift(a, now):
    rows = fetch(a.repo, now - timedelta(days=28), False, now)
    lines = drift_lines(rows, now, a.pct, a.min_minutes)
    for line in lines:
        print(f"{a.repo} {line}")
    return 1 if lines else 0


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report")
    d = sub.add_parser("drift")
    for s in (r, d):
        s.add_argument("--repo", required=True, help="loser-picks or gridkeep")
    r.add_argument("--since", default=(datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d"))
    r.add_argument("--open", action="store_true", help="include open tickets")
    r.add_argument("--csv")
    d.add_argument("--pct", type=float, default=50)
    d.add_argument("--min-minutes", type=float, default=15)
    a = p.parse_args()
    now = datetime.now(timezone.utc)
    if a.cmd == "report":
        cmd_report(a, now)
        return 0
    return cmd_drift(a, now)


if __name__ == "__main__":
    sys.exit(main())
