#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""What is alerting in the home lab: firing now, plus recent history.

Firing alerts come from Grafana (anonymous read). History comes from dungeon's
ops-broker alert log (over ssh, or read directly on dungeon), because it also holds launchd watchdog alerts
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
import socket
import subprocess
import sys
import time
import tomllib
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

GRAFANA = "https://grafana.grehg2.xyz/api"
HOST = os.environ.get("LAB_ALERTS_HOST", "dungeon")
LOG = "~/Library/Logs/ops-broker/alerts.jsonl"
ON_HOST = socket.gethostname().split(".")[0].lower() == HOST.lower()
TAIL = 5000
STALE = timedelta(hours=24)
# Root alerts wait 15m (for:) before firing.
LEAD = timedelta(minutes=20)
DEPS = os.environ.get("LAB_ALERTS_DEPS", "~/Git/home-lab/ops/dependencies.toml")


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
        st = a["status"]
        flag = "silenced" if st.get("silencedBy") else "inhibited" if st.get("inhibitedBy") else ""
        out.append({
            "flag": flag,
            "name": lab.get("alertname", "?"),
            "summary": ann.get("summary", ""),
            "since": started.isoformat(),
            "age": age(max(now - started, timedelta(0))),
            "runbook": ann.get("runbook", ""),
            "labels": lab,
        })
    return sorted(out, key=lambda r: r["since"])


def load_deps(path: str) -> tuple[list[dict], str]:
    """Roots and a warning. A missing file is silent; a broken one warns."""
    try:
        with open(os.path.expanduser(path), "rb") as f:
            roots = tomllib.load(f).get("root", [])
    except FileNotFoundError:
        return [], ""
    except (OSError, tomllib.TOMLDecodeError) as e:
        return [], f"Dependency map {path} unreadable ({e}); no shared-cause grouping."
    try:
        for root in roots:
            for rule in [root["down"], *root.get("explains", [])]:
                re.compile(rule["alert"])
                for rx in rule.get("labels", {}).values():
                    re.compile(rx)
    except (KeyError, TypeError, re.error) as e:
        return [], f"Dependency map {path} invalid ({e!r}); no shared-cause grouping."
    return roots, ""


def matches(rule: dict, alert: dict) -> bool:
    if not re.fullmatch(rule["alert"], alert["name"]):
        return False
    return all(re.search(rx, alert["labels"].get(k, "")) for k, rx in rule.get("labels", {}).items())


def label(alert: dict) -> str:
    """Short name for one alert in the shared-cause list."""
    lab = alert["labels"]
    host = re.match(r"https?://([^./]+)", lab.get("instance", ""))
    return host.group(1) if host else lab.get("app") or alert["name"]


def detail(alert: dict) -> str:
    """Name plus the label that says which one, for unexplained alerts."""
    lab = alert["labels"]
    which = label(alert) if label(alert) != alert["name"] else next(
        (lab[k] for k in ("disk", "repo", "job") if lab.get(k)), "")
    return f"{alert['name']} ({which})" if which and which != alert["name"] else alert["name"]


def counted(names: list[str]) -> list[str]:
    return [n if c == 1 else f"{n} x{c}" for n, c in Counter(names).items()]


def shared_causes(alerts: list[dict], roots: list[dict]) -> dict:
    """Group alerts under a root only when that root's own down alert fires.

    Silenced roots form no group; alerts older than a root by more than
    LEAD cannot be its fallout.
    """
    live = {}
    for root in roots:
        sig = [a for a in alerts if not a["flag"] and matches(root["down"], a)]
        if sig:
            live[root["id"]] = (root, sig, min(datetime.fromisoformat(a["since"]) for a in sig))
    sig_ids = {id(a) for _, sig, _ in live.values() for a in sig}
    owned: dict[str, list[str]] = {rid: [] for rid in live}
    shared: dict[tuple, list[str]] = {}
    unexplained = []
    for a in alerts:
        if id(a) in sig_ids:
            continue
        since = datetime.fromisoformat(a["since"])
        by = tuple(rid for rid, (root, _, start) in live.items()
                   if since >= start - LEAD and any(matches(r, a) for r in root.get("explains", [])))
        if len(by) == 1:
            owned[by[0]].append(label(a))
        elif by:
            shared.setdefault(by, []).append(label(a))
        else:
            unexplained.append(detail(a))
    if not live:
        return {}
    groups = [{"root": rid, "down_alert": sig[0]["name"], "down_label": label(sig[0]),
               "state": root.get("state", "is down"), "explains": counted(owned[rid])}
              for rid, (root, sig, _) in live.items()]
    return {"groups": groups,
            "shared": [{"roots": list(by), "explains": counted(n)} for by, n in shared.items()],
            "unexplained": counted(unexplained)}


def age(delta: timedelta) -> str:
    mins = int(delta.total_seconds() // 60)
    if mins < 60:
        return f"{mins}m"
    if mins < 1440:
        return f"{mins // 60}h"
    return f"{mins // 1440}d"


def read_log(host: str, lines: int = TAIL) -> tuple[list[dict], int]:
    """Parsed rows and the count of lines that would not parse."""
    if ON_HOST:
        with open(os.path.expanduser(LOG)) as f:
            raw = [l for l in f.read().splitlines()[-lines:] if l.strip()]
    else:
        cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", host, f"tail -n {lines} {LOG}"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else f"ssh exit {proc.returncode}")
        raw = [l for l in proc.stdout.splitlines() if l.strip()]
    rows = [r for r in map(parse_row, raw) if r]
    return rows, len(raw) - len(rows)


def parse_row(line: str) -> dict | None:
    try:
        r = json.loads(line)
        r["at"] = datetime.fromisoformat(r["ts"])
    except (ValueError, KeyError, TypeError):
        return None
    return r if r["at"].tzinfo else None


def norm(title: str) -> str:
    """Alert and clear titles differ only by volatile suffixes."""
    t = re.sub(r"\([^)]*\)", "", title.lower())
    return " ".join(t.replace(" still ", " ").split())


def pair(rows: list[dict], now: datetime, days: float) -> list[dict]:
    """Incidents oldest first. Unmatched faults stay OPEN rather than hide."""
    open_: dict[tuple, dict] = {}
    done: list[dict] = []
    for r in sorted(rows, key=lambda r: r["at"]):
        source, title = r.get("source", ""), r.get("title", "")
        key = (source, r.get("key") or norm(title))
        if r.get("kind") == "alert":
            inc = open_.get(key)
            if inc:
                inc["title"], inc["repeats"] = title, inc["repeats"] + 1
            else:
                open_[key] = {"source": source, "title": title, "start": r["at"], "end": None,
                              "repeats": 1, "kind": "alert", "source_cleared": None}
        elif r.get("kind") == "clear":
            inc = open_.pop(key, None)
            if inc:
                inc["end"] = r["at"]
                done.append(inc)
            else:
                for other in open_.values():
                    if other["source"] == source:
                        other["source_cleared"] = r["at"]
        else:
            done.append({"source": source, "title": title, "start": r["at"], "end": r["at"], "repeats": 1, "kind": "info"})
    cutoff = now - timedelta(days=days)
    keep = [i for i in done + list(open_.values()) if i["end"] is None or i["end"] >= cutoff]
    return sorted(keep, key=lambda i: i["start"])


def log_cmd(source: str) -> str:
    tail = f"tail -n 50 ~/Library/Logs/{source}.log"
    return tail if ON_HOST else f"ssh {HOST} {tail}"


def fmt_incident(i: dict, now: datetime) -> str:
    stamp = i["start"].strftime("%a %m-%d %H:%M")
    again = f" (x{i['repeats']})" if i["repeats"] > 1 else ""
    if i["kind"] == "info":
        return f"info   {stamp}  {i['source']}: {i['title']}"
    if i["end"] is None:
        sc = i.get("source_cleared")
        extra = f"; a {i['source']} clear came {sc.strftime('%m-%d %H:%M')} but did not name this" if sc else ""
        return (f"OPEN   {stamp}  {i['source']}: {i['title']}{again}, open {age(now - i['start'])}, no clear yet{extra}"
                f"\n      log: {log_cmd(i['source'])}")
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
    if result["firing"]:
        roots, warn = load_deps(DEPS)
        if warn:
            notes.append(warn)
        try:
            result["shared_cause"] = shared_causes(result["firing"], roots)
        except Exception as e:
            notes.append(f"Dependency grouping failed ({e!r}); ignore it.")

    try:
        rows, skipped = read_log(HOST)
        incidents = pair(rows, now, args.days)
        newest = max((r["at"] for r in rows), default=None)
        prov = f"log: {len(rows)} rows read, {skipped} unparsable, newest " + (newest.strftime("%m-%d %H:%M") if newest else "none")
        if not rows or skipped:
            prov += " (WARNING: log empty or unreadable lines, history may be incomplete)"
        elif now - newest > STALE:
            prov += f" (WARNING: nothing logged for {age(now - newest)})"
        if len(rows) + skipped >= TAIL:
            prov += f" (read only the last {TAIL} lines; older history is cut off)"
        notes.append(prov)
        result["history"] = []
        for i in incidents:
            d = {**i, "start": i["start"].isoformat(), "end": i["end"] and i["end"].isoformat()}
            if i["end"] is None:
                d["log_cmd"] = log_cmd(i["source"])
            result["history"].append(d)
        result["history_source"] = "ops-broker alert log"
        history_lines = [fmt_incident(i, now) for i in incidents]
    except Exception as e:
        notes.append(f"reading the {HOST} alert log failed ({e}); history below is Grafana annotations only, no watchdog alerts.")
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
            rb = f" [runbook: ~/Git/home-lab/docs/runbooks/{a['runbook']}.md]" if a["runbook"] else ""
            fl = f" ({a['flag']}, not paging)" if a["flag"] else ""
            print(f"  {a['age']:>4}  {a['name']}{fl}: {a['summary']}{rb}")
        if not result["firing"]:
            print("  nothing")
        sc = result.get("shared_cause")
        if sc:
            print("\nLIKELY SHARED CAUSE (from ops/dependencies.toml)")
            for g in sc["groups"]:
                sig = g["down_alert"] if g["down_label"] == g["down_alert"] else f"{g['down_alert']}: {g['down_label']}"
                print(f"  {g['root']} {g['state']} ({sig}) \u2192 explains: "
                      + (", ".join(g["explains"]) or "nothing else firing"))
            for g in sc["shared"]:
                print(f"  explained by {' or '.join(g['roots'])}: " + ", ".join(g["explains"]))
            print("  not explained by a known dependency: " + (", ".join(sc["unexplained"]) or "none"))
    print(f"\nHISTORY, last {args.days:g} days ({result['history_source']})")
    for line in history_lines or ["nothing"]:
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
