#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Move Claude Code sessions started outside Herdr into Herdr panes.

A live process can't change terminals, but a session is a transcript on disk:
stop the loose process, then `claude --resume <id>` it in a Herdr terminal.
Dry run by default; `--apply` acts. Reads Claude's own registry
(`~/.claude/sessions/<pid>.json`), one machine at a time through `hc exec`.

  herdr-adopt.py                      # moria, table only
  herdr-adopt.py -m dungeonts -m foundationts
  herdr-adopt.py -m dungeonts --apply --only notes-c2

Sessions that are busy, waiting on a prompt or running a shell command are
skipped: stopping them would lose the turn. Re-run once they go idle.
Phone sessions (`claude remote-control` workers) come back as a normal
interactive session with Remote Control on, which the phone sees as a new
entry with the same history. Background sessions (`claude --bg`) need no
restart: the table prints their `claude attach` command.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys

# Runs on the target machine; prints one JSON list.
COLLECTOR = r'''
import glob, json, os, subprocess, sys, time
home = os.path.expanduser("~")
def ps(*a):
    env = {**os.environ, "TZ": "UTC"}  # procStart is written in UTC
    return subprocess.run(["ps", *a], capture_output=True, text=True, env=env).stdout.strip()
rows = []
for f in glob.glob(home + "/.claude/sessions/*.json"):
    try:
        d = json.load(open(f))
        pid = int(d["pid"])
        os.kill(pid, 0)
    except Exception:
        continue
    ps0 = str(d.get("procStart", ""))
    if ps0.isdigit():  # Linux: clock ticks, field 22 of /proc/<pid>/stat
        try:
            start = open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()[19]
        except OSError:
            continue
        if start != ps0:
            continue
    elif " ".join(ps("-o", "lstart=", "-p", str(pid)).split()) != " ".join(ps0.split()):
        continue
    env = ps("eww", "-o", "command=", "-p", str(pid))
    d["inHerdr"] = " HC_TERMINAL_ID=" in env or " HERDR_ENV=" in env
    d["argv"] = ps("-o", "command=", "-p", str(pid))
    d["hasTranscript"] = bool(glob.glob(home + "/.claude/projects/*/" + d["sessionId"] + ".jsonl"))
    d["cwdExists"] = os.path.isdir(d["cwd"])
    d["idleFor"] = int(time.time() - d.get("statusUpdatedAt", d.get("updatedAt", 0)) / 1000)
    rows.append(d)
print(json.dumps(rows))
'''


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def on(machine: str, cmd: list[str], stdin: str | None = None) -> subprocess.CompletedProcess:
    if machine == "local":
        return run(cmd, input=stdin)
    return run(["hc", "exec", "--on", machine, *(["-i"] if stdin else []), *cmd], input=stdin)


def collect(machine: str) -> list[dict]:
    r = on(machine, ["python3", "-c", COLLECTOR])
    if r.returncode:
        sys.exit(f"{machine}: collector failed: {r.stderr.strip()[:300]}")
    return json.loads(r.stdout)


def flag(argv: str, name: str) -> str | None:
    m = re.search(rf"(?:^|\s){name}[= ](\S+)", argv)
    return m.group(1) if m else None


def classify(d: dict, min_idle: int) -> tuple[str, str]:
    """Return (action, why). action is one of resume, attach, skip."""
    if d["kind"] == "bg":
        return "attach", f"claude attach {d.get('jobId', '?')}"
    if d["inHerdr"]:
        return "skip", "already in Herdr"
    if not d["hasTranscript"]:
        return "skip", "no transcript to resume"
    if not d["cwdExists"]:
        return "skip", "cwd is gone"
    if d["status"] != "idle":
        return "skip", f"{d['status']}" + (f" ({d['waitingFor']})" if d.get("waitingFor") else "")
    if d["idleFor"] < min_idle:
        return "skip", f"idle only {d['idleFor']}s"
    return "resume", "phone" if d["entrypoint"] == "sdk-cli" else "terminal"


def herdr_name(d: dict) -> str:
    return re.sub(r"[^a-z0-9_-]+", "-", (d.get("name") or "claude").lower()).strip("-")[:32] or "claude"


def resume_cmd(d: dict) -> list[str]:
    cmd = ["claude", "--resume", d["sessionId"]]
    if d.get("name"):
        cmd += ["--name", d["name"]]
    for f in ("--model", "--permission-mode"):
        v = flag(d["argv"], f)
        if v:
            cmd += [f, v]
    if d.get("bridgeSessionId") or d["entrypoint"] == "sdk-cli":
        cmd += ["--remote-control"]
    return cmd


def adopt(machine: str, d: dict) -> str:
    kill = on(machine, ["kill", "-TERM", str(d["pid"])])
    if kill.returncode:
        return f"FAILED stop: {kill.stderr.strip()}"
    wait = on(machine, ["sh", "-c", f"for i in $(seq 20); do kill -0 {d['pid']} 2>/dev/null || exit 0; sleep 0.5; done; exit 1"])
    if wait.returncode:
        return "FAILED: process still alive after 10s, left it running"
    cmd = ["herdr-app", "do", "space.new", "--name", d.get("name") or herdr_name(d), "--folder", d["cwd"],
           "--argv", json.dumps(resume_cmd(d)), "--focus", "false"]
    if machine != "local":
        cmd += ["--machine", machine]
    r = run(cmd)
    if r.returncode:
        return f"STOPPED but FAILED to start: {(r.stderr or r.stdout).strip()[:200]}; resume by hand: {shlex.join(resume_cmd(d))}"
    return "now " + " ".join(str(v) for v in json.loads(r.stdout).values())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-m", "--machine", action="append", help="hc machine name (default: this one)")
    ap.add_argument("--apply", action="store_true", help="stop and resume; default is a dry run")
    ap.add_argument("--only", action="append", help="session name, pid or session ID; repeatable")
    ap.add_argument("--min-idle", type=int, default=60, help="seconds a session must have been idle")
    args = ap.parse_args()

    for machine in args.machine or ["local"]:
        rows = sorted(collect(machine), key=lambda d: d["startedAt"])
        print(f"\n== {machine}: {len(rows)} live sessions")
        for d in rows:
            action, why = classify(d, args.min_idle)
            if action == "skip" and why == "already in Herdr":
                continue
            picked = not args.only or {str(d["pid"]), d["sessionId"], d.get("name")} & set(args.only)
            result = ""
            if args.apply and action == "resume" and picked:
                result = " -> " + adopt(machine, d)
            kind = "bg" if d["kind"] == "bg" else ("phone" if d["entrypoint"] == "sdk-cli" else "cli")
            print(f"{action:7} {d['pid']:>6} {kind:5} {d.get('name', '')[:28]:28} {d['cwd'][-34:]:34} {why}{result}")
    if not args.apply:
        print("\ndry run: pass --apply (optionally --only <name>) to move the 'resume' rows")


if __name__ == "__main__":
    main()
