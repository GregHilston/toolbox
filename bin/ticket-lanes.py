#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Ticket-flow report from `stage:*` labels on any GitHub repo, and drift alerts.

    ticket-lanes.py report --repo OWNER/NAME [--since 2026-11-13] [--until 2026-11-14T09:00]
                           [--open] [--stage-prefix stage:] [--active building,fixing,landing]
                           [--bucket 2] [--json] [--csv out.csv]
    ticket-lanes.py report --repo NAME --compare SINCE1 UNTIL1 SINCE2 UNTIL2
    ticket-lanes.py drift  --repo NAME [--pct 50] [--min-minutes 15]

A bare NAME means owner GregHilston. Times without a zone are local time.
Reads each issue's timeline over GraphQL: a stage interval runs from `labeled`
to `unlabeled`, else to close, else to now. "unlabeled" is the gap from the
last stage label's removal to close. Per-ticket time sums across fix rounds.
Tickets are in a window by close time (open ones too with --open).
Refuses to run under 500 GraphQL points left; prints the points spent on stderr.
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
from datetime import datetime, timedelta, timezone

OWNER = "GregHilston"
GAP = "unlabeled"
MIN_SAMPLE = 5
RESERVE = 500
PREFIX = "stage:"
ACTIVE = "building,fixing,landing"
REWORK = "fixing"


def parse(ts: str) -> datetime:
    """Parse a GitHub ISO timestamp."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def parse_when(text: str) -> datetime:
    """ISO date or datetime to UTC; no zone means local time."""
    d = datetime.fromisoformat(text)
    return (d.astimezone() if d.tzinfo is None else d).astimezone(timezone.utc)


def stage_spans(events, closed, now, prefix=PREFIX):
    """Return [(stage, start, end)] for one ticket's stage labels."""
    end_of_time = closed or now
    opened, spans = {}, []
    for e in sorted(events, key=lambda e: e["created_at"]):
        name = (e.get("label") or {}).get("name", "")
        if not name.startswith(prefix):
            continue
        t = parse(e["created_at"])
        if e["event"] == "labeled":
            opened.setdefault(name, t)
        elif e["event"] == "unlabeled" and name in opened:
            spans.append((name, opened.pop(name), t))
    return spans + [(n, s, end_of_time) for n, s in opened.items()]


def ticket_stats(events, closed, now, prefix=PREFIX):
    """Return {stage: (seconds, entries)} for one ticket."""
    spans = stage_spans(events, closed, now, prefix)
    out = {}
    for name, s, e in spans:
        sec, n = out.get(name, (0, 0))
        out[name] = (sec + max(0, int((e - s).total_seconds())), n + 1)
    if closed and spans:
        last = max(e for _, _, e in spans)
        if closed > last:
            out[GAP] = (int((closed - last).total_seconds()), 1)
    return out


def make_row(number, created, closed, events, now, prefix=PREFIX):
    """Bundle one ticket's parsed events with its derived spans and stats."""
    return {"number": number, "created_at": created, "closed_at": closed, "events": events,
            "spans": stage_spans(events, closed, now, prefix),
            "stats": ticket_stats(events, closed, now, prefix)}


def union_seconds(intervals) -> float:
    """Total length of the union of (start, end) intervals."""
    total, cur_s, cur_e = 0.0, None, None
    for s, e in sorted(intervals):
        if cur_e is None or s > cur_e:
            if cur_e is not None:
                total += (cur_e - cur_s).total_seconds()
            cur_s, cur_e = s, e
        elif e > cur_e:
            cur_e = e
    if cur_e is not None:
        total += (cur_e - cur_s).total_seconds()
    return total


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


def pct_of(vals, q):
    """Nearest-rank-ish percentile of a non-empty list."""
    vals = sorted(vals)
    return vals[min(len(vals) - 1, int(q * len(vals)))]


def in_window(row, since, until, include_open):
    """Closed in [since, until), or open when include_open."""
    c = row["closed_at"]
    return include_open if c is None else since <= c < until


def stage_table(rows):
    """Per stage: tickets, entries, median/p90 minutes, total hours."""
    per, entries = defaultdict(list), defaultdict(int)
    for r in rows:
        for stage, (sec, n) in r["stats"].items():
            per[stage].append(sec)
            entries[stage] += n
    return {st: {"tickets": len(v), "entries": entries[st],
                 "median_min": statistics.median(v) / 60,
                 "p90_min": pct_of(v, 0.9) / 60, "total_h": sum(v) / 3600}
            for st, v in sorted(per.items())}


def throughput(rows, since, until, bucket_hours=2.0):
    """Tickets closed per hour, and counts per bucket from `since`."""
    hours = max((until - since).total_seconds() / 3600, 1e-9)
    step = timedelta(hours=bucket_hours)
    n = max(1, int(-(-(until - since) // step)))
    counts = [0] * n
    closed = 0
    for r in rows:
        c = r["closed_at"]
        if c and since <= c < until:
            counts[int((c - since) // step)] += 1
            closed += 1
    return {"closed": closed, "per_hour": closed / hours, "bucket_hours": bucket_hours,
            "buckets": [{"start": (since + i * step).isoformat(), "closed": c}
                        for i, c in enumerate(counts)]}


def lead_times(rows):
    """Lead time (first stage label to close) split into staged and unstaged time."""
    lead, staged, gap = [], [], []
    for r in rows:
        c = r["closed_at"]
        if not c or not r["spans"]:
            continue
        first = min(s for _, s, _ in r["spans"])
        span = max(0.0, (c - first).total_seconds())
        stg = min(span, union_seconds([(s, min(e, c)) for _, s, e in r["spans"] if s < c]))
        lead.append(span)
        staged.append(stg)
        gap.append(span - stg)
    if not lead:
        return {"tickets": 0}
    m = statistics.median
    return {"tickets": len(lead), "lead_median_min": m(lead) / 60,
            "lead_p90_min": pct_of(lead, 0.9) / 60, "staged_median_min": m(staged) / 60,
            "no_stage_median_min": m(gap) / 60}


def flow_efficiency(rows, active, prefix=PREFIX):
    """Share of lead time spent in active stages, over closed staged tickets."""
    work = lead = 0.0
    for r in rows:
        c = r["closed_at"]
        if not c or not r["spans"]:
            continue
        first = min(s for _, s, _ in r["spans"])
        lead += max(0.0, (c - first).total_seconds())
        work += union_seconds([(s, min(e, c)) for n, s, e in r["spans"]
                               if n.removeprefix(prefix) in active and s < c])
    return {"active": sorted(active), "efficiency": work / lead if lead else None,
            "active_h": work / 3600, "lead_h": lead / 3600}


def rework(rows, stage=REWORK, prefix=PREFIX):
    """Share of staged tickets that entered the fix stage, and rounds per ticket."""
    name = prefix + stage
    staged = [r for r in rows if r["spans"]]
    rounds = [r["stats"].get(name, (0, 0))[1] for r in staged]
    hit = [x for x in rounds if x]
    return {"tickets": len(staged), "share": len(hit) / len(staged) if staged else None,
            "rounds_per_ticket": sum(rounds) / len(staged) if staged else None,
            "rounds_per_fixed_ticket": sum(hit) / len(hit) if hit else None}


def wip(rows, since, until):
    """Max and time-weighted mean tickets in each stage within [since, until)."""
    marks = defaultdict(list)
    for r in rows:
        for n, s, e in r["spans"]:
            s, e = max(s, since), min(e, until)
            if s < e:
                marks[n] += [(s, 1), (e, -1)]
    window = (until - since).total_seconds()
    out = {}
    for n, ms in sorted(marks.items()):
        cur = peak = 0
        area = 0.0
        last = since
        for t, d in sorted(ms, key=lambda m: (m[0], m[1])):
            area += cur * (t - last).total_seconds()
            cur += d
            peak = max(peak, cur)
            last = t
        out[n] = {"max": peak, "mean": area / window if window else 0.0}
    return out


def quality(rows, prefix=PREFIX):
    """Tickets with overlapping stage labels, and closed ones with a label still on."""
    overlap = left_on = 0
    for r in rows:
        on, over = set(), False
        for e in sorted(r["events"], key=lambda e: (e["created_at"], e["event"] == "labeled")):
            n = (e.get("label") or {}).get("name", "")
            if not n.startswith(prefix):
                continue
            if e["event"] == "labeled":
                on.add(n)
                over = over or len(on) > 1
            elif e["event"] == "unlabeled":
                on.discard(n)
        overlap += over
        left_on += bool(r["closed_at"] and on)
    return {"overlapping_stage_labels": overlap, "closed_with_stage_label": left_on}


def build_report(rows, since, until, now, include_open=False, prefix=PREFIX,
                 active=frozenset(ACTIVE.split(",")), bucket_hours=2.0, rework_stage=REWORK):
    """Every metric for the tickets in one window, as a plain dict."""
    sel = [r for r in rows if in_window(r, since, until, include_open)]
    end = min(until, now)
    return {"since": since.isoformat(), "until": until.isoformat(), "tickets": len(sel),
            "stages": stage_table(sel),
            "throughput": throughput(sel, since, until, bucket_hours),
            "lead_time": lead_times(sel),
            "flow_efficiency": flow_efficiency(sel, set(active), prefix),
            "rework": rework(sel, rework_stage, prefix),
            "wip": wip(sel, since, end),
            "quality": quality(sel, prefix)}


# GraphQL layer. 25 an issues page: 100 returns stale timelines (docs/github-api.md).
SPEND = {"cost": 0, "remaining": None}
EVENTS = "[LABELED_EVENT, UNLABELED_EVENT, CLOSED_EVENT, REOPENED_EVENT]"
TIMELINE = """
          pageInfo { hasNextPage endCursor }
          nodes {
            __typename
            ... on LabeledEvent { createdAt label { name } }
            ... on UnlabeledEvent { createdAt label { name } }
            ... on ClosedEvent { createdAt }
            ... on ReopenedEvent { createdAt }
          }"""
QUERY = """
query($owner: String!, $name: String!, $since: DateTime!, $after: String) {
  rateLimit { cost remaining }
  repository(owner: $owner, name: $name) {
    issues(first: 25, after: $after, states: %s, filterBy: {since: $since}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        id number closedAt createdAt
        timelineItems(first: 100, itemTypes: %s) {%s
        }
      }
    }
  }
}
"""
MORE = """
query($id: ID!, $after: String) {
  rateLimit { cost remaining }
  node(id: $id) { ... on Issue { timelineItems(first: 100, after: $after, itemTypes: %s) {%s
  } } }
}
""" % (EVENTS, TIMELINE)


def gh(*args):
    """Run gh with retries; exit 2 on failure (1 is reserved for drift found)."""
    for attempt in range(4):
        r = subprocess.run(["gh", *args], capture_output=True, text=True)
        if not r.returncode:
            return r.stdout
        time.sleep(1 + attempt)
    print(f"gh {' '.join(args[:3])}: {r.stderr.strip()}", file=sys.stderr)
    sys.exit(2)


def graphql(query, **variables):
    """Run one GraphQL query and tally its rateLimit cost."""
    args = ["api", "graphql", "-f", f"query={query}"]
    for k, v in variables.items():
        if v is not None:
            args += ["-f", f"{k}={v}"]
    out = json.loads(gh(*args))
    if out.get("errors"):
        print(f"ticket-lanes: GraphQL error: {out['errors'][0].get('message')}", file=sys.stderr)
        sys.exit(2)
    rl = out["data"].get("rateLimit")
    if rl:
        SPEND["cost"] += rl["cost"]
        SPEND["remaining"] = rl["remaining"]
    return out["data"]


def check_quota(reserve=RESERVE):
    """Exit 2 rather than spend the orchestrators' shared GitHub quota."""
    # rate_limit itself costs no quota.
    left = json.loads(gh("api", "rate_limit"))["resources"]["graphql"]
    if left["remaining"] < reserve:
        reset = datetime.fromtimestamp(left["reset"]).strftime("%H:%M")
        print(f"ticket-lanes: {left['remaining']} GitHub GraphQL points left, under the "
              f"{reserve} minimum; retry after {reset}", file=sys.stderr)
        sys.exit(2)


KINDS = {"LabeledEvent": "labeled", "UnlabeledEvent": "unlabeled",
         "ClosedEvent": "closed", "ReopenedEvent": "reopened"}


def as_events(nodes):
    """GraphQL timeline nodes to {event, created_at, label} dicts."""
    return [{"event": KINDS[n["__typename"]], "created_at": n["createdAt"], "label": n.get("label")}
            for n in nodes if n.get("__typename") in KINDS
            and (n["__typename"] not in ("LabeledEvent", "UnlabeledEvent") or n.get("label"))]


def full_timeline(issue):
    """All events of an issue, paging its timeline past 100."""
    tl = issue["timelineItems"]
    nodes = list(tl["nodes"])
    while tl["pageInfo"]["hasNextPage"]:
        tl = graphql(MORE, id=issue["id"], after=tl["pageInfo"]["endCursor"])["node"]["timelineItems"]
        nodes += tl["nodes"]
    return as_events(nodes)


def fetch(owner, repo, since, include_open, now, prefix=PREFIX):
    """Rows for tickets closed since `since` (and open ones with include_open)."""
    check_quota()
    # filterBy.since is update time, a superset of the window.
    floor = since - timedelta(days=60) if include_open else since
    states = "[OPEN, CLOSED]" if include_open else "[CLOSED]"
    query = QUERY % (states, EVENTS, TIMELINE)
    keep, after = [], None
    while True:
        page = graphql(query, owner=owner, name=repo, after=after,
                       since=floor.strftime("%Y-%m-%dT%H:%M:%SZ"))["repository"]["issues"]
        for i in page["nodes"]:
            closed = parse(i["closedAt"]) if i["closedAt"] else None
            created = parse(i["createdAt"])
            if closed and closed < since:
                continue
            if not closed and not (include_open and created >= floor):
                continue
            keep.append(make_row(i["number"], created, closed, full_timeline(i), now, prefix))
        if not page["pageInfo"]["hasNextPage"]:
            return keep
        after = page["pageInfo"]["endCursor"]


def split_repo(text):
    """OWNER/NAME or bare NAME to (owner, name)."""
    owner, _, name = text.rpartition("/")
    return owner or OWNER, name


def fmt(x, spec=".1f", none="-"):
    """Format a number, or a dash for None."""
    return none if x is None else format(x, spec)


def render(title, rep):
    """Plain-text tables for one report."""
    o = [f"\n{title}: {rep['tickets']} tickets, {rep['since'][:16]} to {rep['until'][:16]} UTC",
         f"  {'stage':<18}{'tickets':>8}{'entries':>8}{'median m':>10}{'p90 m':>8}{'total h':>9}"]
    for st, v in rep["stages"].items():
        o.append(f"  {st:<18}{v['tickets']:>8}{v['entries']:>8}{v['median_min']:>10.1f}"
                 f"{v['p90_min']:>8.1f}{v['total_h']:>9.1f}")
    t = rep["throughput"]
    o += ["", f"throughput: {t['closed']} closed, {t['per_hour']:.2f}/h; per {t['bucket_hours']:g} h:",
          "  " + " ".join(str(b["closed"]) for b in t["buckets"])]
    lt = rep["lead_time"]
    if lt["tickets"]:
        o += ["", f"lead time ({lt['tickets']} closed, first stage label to close): "
              f"median {lt['lead_median_min']:.0f} m, p90 {lt['lead_p90_min']:.0f} m",
              f"  cycle: staged median {lt['staged_median_min']:.0f} m, "
              f"no stage label median {lt['no_stage_median_min']:.0f} m"]
    fe = rep["flow_efficiency"]
    eff = fmt(None if fe["efficiency"] is None else fe["efficiency"] * 100, ".0f")
    o += ["", f"flow efficiency: {eff}% ({fe['active_h']:.1f} h in {','.join(fe['active'])} "
          f"of {fe['lead_h']:.1f} h lead)"]
    rw = rep["rework"]
    o.append(f"rework: {fmt(None if rw['share'] is None else rw['share'] * 100, '.0f')}% of "
             f"{rw['tickets']} staged tickets fixed; {fmt(rw['rounds_per_ticket'], '.2f')} rounds "
             f"per ticket, {fmt(rw['rounds_per_fixed_ticket'], '.2f')} per fixed ticket")
    o += ["", f"  {'wip':<18}{'max':>5}{'mean':>7}"]
    o += [f"  {st:<18}{v['max']:>5}{v['mean']:>7.2f}" for st, v in rep["wip"].items()]
    q = rep["quality"]
    o.append(f"\nodd: {q['overlapping_stage_labels']} tickets with overlapping stage labels; "
             f"{q['closed_with_stage_label']} closed with a stage label still on")
    return "\n".join(o)


def render_compare(a, b):
    """Two reports side by side on their headline numbers."""
    def rowof(rep):
        return {"tickets": rep["tickets"], "closed/h": rep["throughput"]["per_hour"],
                "lead median m": rep["lead_time"].get("lead_median_min"),
                "flow eff %": None if rep["flow_efficiency"]["efficiency"] is None
                else rep["flow_efficiency"]["efficiency"] * 100,
                "rework %": None if rep["rework"]["share"] is None else rep["rework"]["share"] * 100}
    ra, rb = rowof(a), rowof(b)
    o = [f"\ncompare   A {a['since'][:16]}..{a['until'][:16]}   B {b['since'][:16]}..{b['until'][:16]}",
         f"  {'':<18}{'A':>10}{'B':>10}"]
    o += [f"  {k:<18}{fmt(ra[k], '.2f'):>10}{fmt(rb[k], '.2f'):>10}" for k in ra]
    o += ["", f"  {'stage median m':<18}{'A':>10}{'B':>10}"]
    for st in sorted(set(a["stages"]) | set(b["stages"])):
        va = a["stages"].get(st, {}).get("median_min")
        vb = b["stages"].get(st, {}).get("median_min")
        o.append(f"  {st:<18}{fmt(va):>10}{fmt(vb):>10}")
    return "\n".join(o)


def write_csv(path, rows):
    """Per-ticket, per-stage rows."""
    with open(path, "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["number", "closed_at", "stage", "seconds", "entries"])
        for r in rows:
            for stage, (sec, n) in sorted(r["stats"].items()):
                wr.writerow([r["number"], r["closed_at"] or "", stage, sec, n])


def cmd_report(a, now):
    owner, repo = split_repo(a.repo)
    if a.compare:
        w = [parse_when(x) for x in a.compare]
        windows = [(w[0], w[1]), (w[2], w[3])]
    else:
        windows = [(parse_when(a.since), parse_when(a.until) if a.until else now)]
    rows = fetch(owner, repo, min(s for s, _ in windows), a.open, now, a.stage_prefix)
    active = set(a.active.split(","))
    reps = [build_report(rows, s, u, now, a.open, a.stage_prefix, active, a.bucket, a.rework)
            for s, u in windows]
    if a.json:
        print(json.dumps({"repo": f"{owner}/{repo}", "reports": reps}, indent=2))
    elif a.compare:
        print(render_compare(*reps))
        for name, rep in zip("AB", reps):
            print(render(f"{owner}/{repo} {name}", rep))
    else:
        print(render(f"{owner}/{repo}", reps[0]))
    if a.csv:
        write_csv(a.csv, [r for r in rows if any(in_window(r, s, u, a.open) for s, u in windows)])
    print(f"ticket-lanes: GraphQL cost {SPEND['cost']} points, {SPEND['remaining']} remaining",
          file=sys.stderr)


def cmd_drift(a, now):
    owner, repo = split_repo(a.repo)
    rows = [r for r in fetch(owner, repo, now - timedelta(days=28), False, now) if r["closed_at"]]
    lines = drift_lines(rows, now, a.pct, a.min_minutes)
    for line in lines:
        print(f"{repo} {line}")
    return 1 if lines else 0


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report")
    d = sub.add_parser("drift")
    for s in (r, d):
        s.add_argument("--repo", required=True, help="OWNER/NAME, or NAME for GregHilston")
    r.add_argument("--since", default=(datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d"))
    r.add_argument("--until", help="default: now")
    r.add_argument("--compare", nargs=4, metavar=("SINCE1", "UNTIL1", "SINCE2", "UNTIL2"))
    r.add_argument("--open", action="store_true", help="include open tickets")
    r.add_argument("--stage-prefix", default=PREFIX)
    r.add_argument("--active", default=ACTIVE, help="stages counted as working")
    r.add_argument("--rework", default=REWORK, help="stage that marks a fix round")
    r.add_argument("--bucket", type=float, default=2, help="throughput bucket, hours")
    r.add_argument("--json", action="store_true")
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
