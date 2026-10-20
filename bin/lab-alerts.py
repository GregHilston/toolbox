#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""What is alerting in the home lab: firing now, plus recent history.

Firing alerts come from Grafana (anonymous read). History comes from dungeon's
ops-broker alert log over ssh, because it also holds launchd watchdog alerts
Grafana never sees. If ssh fails, history falls back to Grafana annotations.
Read-only.

Usage:
    lab-alerts              # firing now + last 3 days
    lab-alerts --days 7
    lab-alerts --json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

GRAFANA = "https://grafana.grehg2.xyz/api"
HOST = os.environ.get("LAB_ALERTS_HOST", "dungeon")
LOG = "~/Library/Logs/ops-broker/alerts.jsonl"
# Pairing looks back a week so an older still-open alert is not missed.
LOOKBACK = timedelta(days=7)


def get_json(url: str):
    with urllib.request.urlopen(url, timeout=15) as resp:
        return json.loads(resp.read())


def firing(now: datetime) -> list[dict]:
    rows = get_json(f"{GRAFANA}/alertmanager/grafana/api/v2/alerts")
    out = []
    for a in rows:
        if a["status"]["state"] != "active":
            continue
        lab, ann = a["labels"], a["annotations"]
        started = datetime.fromisoformat(a["startsAt"])
        out.append({
            "name": lab.get("alertname", "?"),
            "summary": ann.get("summary", ""),
            "since": started.isoformat(),
            "age": age(now - started),
            "runbook": ann.get("runbook", ""),
        })
    return sorted(out, key=lambda r: r["since"])


def age(delta: timedelta) -> str:
    mins = int(delta.total_seconds() // 60)
    if mins < 60:
        return f"{mins}m"
    if mins < 2880:
        return f"{mins // 60}h"
    return f"{mins // 1440}d"


def read_log(host: str, lines: int = 5000) -> list[dict]:
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", host, f"tail -n {lines} {LOG}"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else f"ssh exit {proc.returncode}")
    return [r for r in map(parse_row, proc.stdout.splitlines()) if r]


def parse_row(line: str) -> dict | None:
    try:
        r = json.loads(line)
        r["at"] = datetime.strptime(r["ts"], "%Y-%m-%dT%H:%M:%S%z")
    except (ValueError, KeyError):
        return None
    return r


def pair(rows: list[dict], now: datetime, days: float) -> list[dict]:
    """Incidents oldest first: repeats merge, a clear closes, info stands alone."""
    rows = sorted((r for r in rows if r["at"] >= now - LOOKBACK), key=lambda r: r["at"])
    open_: dict[tuple, dict] = {}
    done: list[dict] = []
    for r in rows:
        source, title = r.get("source", ""), r.get("title", "")
        key = (source, r.get("key") or "")
        if r.get("kind") == "alert":
            inc = open_.get(key)
            if inc:
                inc["title"], inc["repeats"] = title, inc["repeats"] + 1
            else:
                open_[key] = {"source": source, "title": title, "start": r["at"], "end": None, "repeats": 1, "kind": "alert"}
        elif r.get("kind") == "clear":
            # A keyless clear means the whole source is healthy again.
            for k in [k for k in open_ if k == key or (not r.get("key") and k[0] == source)]:
                inc = open_.pop(k)
                inc["end"] = r["at"]
                done.append(inc)
        else:
            done.append({"source": source, "title": title, "start": r["at"], "end": r["at"], "repeats": 1, "kind": "info"})
    cutoff = now - timedelta(days=days)
    keep = [i for i in done + list(open_.values()) if (i["end"] or now) >= cutoff]
    return sorted(keep, key=lambda i: i["start"])


def fmt_incident(i: dict, now: datetime) -> str:
    stamp = i["start"].strftime("%a %m-%d %H:%M")
    again = f" (x{i['repeats']})" if i["repeats"] > 1 else ""
    if i["kind"] == "info":
        return f"info   {stamp}  {i['source']}: {i['title']}"
    if i["end"] is None:
        return f"OPEN   {stamp}  {i['source']}: {i['title']}{again}, open {age(now - i['start'])}, no clear yet"
    return f"closed {stamp}  {i['source']}: {i['title']}{again}, lasted {age(i['end'] - i['start'])}"


def annotations(now: datetime, days: float) -> list[dict]:
    since = int((now.timestamp() - days * 86400) * 1000)
    rows = get_json(f"{GRAFANA}/annotations?type=alert&limit=300&from={since}")
    out = []
    for r in sorted(rows, key=lambda r: r["time"]):
        if r["time"] < since:
            continue
        new, prev = r.get("newState", ""), r.get("prevState", "")
        if not (new.startswith("Alerting") or (new.startswith("Normal") and prev.startswith("Alerting"))):
            continue
        text = r.get("text", "")
        inst = re.search(r"instance=([^,}]+)", text)
        out.append({
            "at": datetime.fromtimestamp(r["time"] / 1000, timezone.utc).astimezone().isoformat(),
            "state": "FIRING" if new.startswith("Alerting") else "cleared",
            "name": text.split(" {")[0],
            "instance": inst.group(1) if inst else "",
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--days", type=float, default=3, help="history window (default 3)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    now = datetime.now(timezone.utc).astimezone()
    result: dict = {}
    notes: list[str] = []

    try:
        result["firing"] = firing(now)
    except Exception as e:
        result["firing"] = None
        notes.append(f"Could not read Grafana firing alerts: {e}")

    try:
        incidents = pair(read_log(HOST), now, args.days)
        result["history"] = [{**i, "start": i["start"].isoformat(), "end": i["end"] and i["end"].isoformat()} for i in incidents]
        result["history_source"] = "ops-broker alert log"
        history_lines = [fmt_incident(i, now) for i in incidents]
    except Exception as e:
        notes.append(f"ssh to {HOST} failed ({e}); history below is Grafana annotations only, no watchdog alerts.")
        try:
            ann = annotations(now, args.days)
        except Exception as e2:
            ann = []
            notes.append(f"Grafana annotations failed too: {e2}")
        result["history"], result["history_source"] = ann, "grafana annotations"
        history_lines = [f"{a['state']:7} {a['at'][5:16].replace('T', ' ')}  {a['name']} {a['instance']}".rstrip() for a in ann]

    if args.json:
        result["notes"] = notes
        print(json.dumps(result, indent=1, default=str))
        return 0

    for n in notes:
        print(n)
    if result["firing"] is not None:
        print(f"FIRING NOW ({len(result['firing'])})")
        for a in result["firing"]:
            rb = f" [runbook: {a['runbook']}]" if a["runbook"] else ""
            print(f"  {a['age']:>4}  {a['name']}: {a['summary']}{rb}")
        if not result["firing"]:
            print("  nothing")
    print(f"\nHISTORY, last {args.days:g} days ({result['history_source']})")
    for line in history_lines or ["nothing"]:
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
