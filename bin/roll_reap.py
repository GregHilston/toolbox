"""Kill leftover Godot gate processes that hold a shift roll open.

The roll waits for Claude Code's `background_tasks` to reach zero. That list
lives inside Claude Code: no file or process says which task belongs to which
agent. So this works on processes instead, with one honest proxy for "an agent
is still running": a subagent transcript written to in the last ROLL_AGENT_QUIET
seconds. While one exists, nothing is killed.

A process is reaped when all of these hold:
  - its program is godot, gate_test.sh or verify.sh (ROLL_REAP_NAMES adds more),
  - a Claude Code process is among its ancestors, or it was orphaned to init,
  - its cwd is a scratchpad or sits under a `worktrees/` directory,
  - that cwd belongs to the rolling repo: its checkout or one of its git
    worktrees (same git common dir), or one of its Claude scratchpads,
  - it is older than ROLL_REAP_GRACE seconds (default 900),
  - its cwd is under ROLL_REAP_ROOT, when that is set.
"""

from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

GRACE = int(os.environ.get("ROLL_REAP_GRACE", 15 * 60))
AGENT_QUIET = int(os.environ.get("ROLL_AGENT_QUIET", 120))
NAMES = {"godot", "gate_test.sh", "verify.sh", *filter(None, os.environ.get("ROLL_REAP_NAMES", "").split(","))}
SCRATCH = re.compile(r"(^|/)(claude-\d+|scratchpad)(/|$)")
PROJECTS = Path(os.environ.get("CLAUDE_PROJECTS_DIR") or Path.home() / ".claude/projects")
# Tests set it: unscoped, they reaped live lanes.
ROOT = os.environ.get("ROLL_REAP_ROOT", "")


@dataclass
class Proc:
    pid: int
    ppid: int
    pgid: int
    age: int
    command: str
    cwd: str = ""
    owner: int | None = None


def seconds(etime: str) -> int:
    """ps etime: [[dd-]hh:]mm:ss."""
    days, _, rest = etime.rpartition("-")
    parts = [int(p) for p in rest.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    return (int(days or 0) * 24 + parts[0]) * 3600 + parts[1] * 60 + parts[2]


def snapshot() -> dict[int, Proc]:
    out = subprocess.run(["ps", "-axo", "pid=,ppid=,pgid=,etime=,command="], capture_output=True, text=True).stdout
    procs = {}
    for line in out.splitlines():
        f = line.split(None, 4)
        if len(f) == 5:
            procs[int(f[0])] = Proc(int(f[0]), int(f[1]), int(f[2]), seconds(f[3]), f[4])
    return procs


def program(command: str) -> str:
    """The thing being run: a script's name when an interpreter runs it."""
    words = command.split()
    names = [os.path.basename(w) for w in words[:3]]
    for n in names:
        if n in NAMES:
            return n
    return ""


def claude_ancestor(procs: dict[int, Proc], proc: Proc) -> int | None:
    seen = set()
    pid = proc.ppid
    while pid in procs and pid not in seen:
        seen.add(pid)
        p = procs[pid]
        if os.path.basename(p.command.split()[0]) == "claude":
            return pid
        pid = p.ppid
    return None


def orphan(procs: dict[int, Proc], proc: Proc) -> bool:
    # systemd --user is a subreaper: Linux orphans land there, not on pid 1.
    parent = procs.get(proc.ppid)
    return proc.ppid == 1 or (parent is not None and os.path.basename(parent.command.split()[0]) == "systemd")


def slug(path: str) -> str:
    """Claude Code's project folder name for a path."""
    return re.sub(r"[^A-Za-z0-9]", "-", path)


def common_dir(path: str) -> str | None:
    out = subprocess.run(["git", "-C", path, "rev-parse", "--path-format=absolute", "--git-common-dir"],
                         capture_output=True, text=True)  # fmt: skip
    return os.path.realpath(out.stdout.strip()) if out.returncode == 0 else None


def belongs(cwd: str, repo: str, repo_git: str | None) -> bool:
    """Whether a gate running in `cwd` is the rolling repo's."""
    if SCRATCH.search(cwd):
        return f"/{slug(repo)}/" in cwd + "/"
    return repo_git is not None and common_dir(cwd) == repo_git


def cwds(pids: list[int]) -> dict[int, str]:
    if not pids:
        return {}
    if Path("/proc/self/cwd").exists():  # foundation has no lsof
        found = {}
        for pid in pids:
            try:
                found[pid] = os.path.realpath(os.readlink(f"/proc/{pid}/cwd"))
            except OSError:
                pass
        return found
    out = subprocess.run(["lsof", "-a", "-d", "cwd", "-Fpn", "-p", ",".join(map(str, pids))],
                         capture_output=True, text=True).stdout  # fmt: skip
    found, pid = {}, 0
    for line in out.splitlines():
        if line.startswith("p"):
            pid = int(line[1:])
        elif line.startswith("n"):
            found[pid] = os.path.realpath(line[1:])
    return found


def running_agent(now: float) -> Path | None:
    """The newest subagent transcript touched within the quiet window."""
    newest = None
    for f in PROJECTS.glob("*/*/subagents/agent-*.jsonl"):
        try:
            m = f.stat().st_mtime
        except OSError:
            continue
        if now - m < AGENT_QUIET and (newest is None or m > newest[0]):
            newest = (m, f)
    return newest[1] if newest else None


def candidates(procs: dict[int, Proc], repo: str) -> list[Proc]:
    mine = {os.getpid(), os.getppid()}
    found = [p for p in procs.values() if p.pid not in mine and program(p.command)]
    where = cwds([p.pid for p in found])
    repo = os.path.realpath(repo)
    repo_git = common_dir(repo)
    keep = []
    for p in found:
        p.cwd = where.get(p.pid, "")
        p.owner = claude_ancestor(procs, p)
        if ROOT and not (p.cwd + "/").startswith(ROOT.rstrip("/") + "/"):
            continue
        if (p.owner or orphan(procs, p)) and (SCRATCH.search(p.cwd) or "/worktrees/" in p.cwd + "/") \
                and belongs(p.cwd, repo, repo_git):
            keep.append(p)
    return keep


def kill_group(p: Proc, procs: dict[int, Proc]) -> None:
    # A group shared with a shell or claude would take them down too.
    shared = any(q.pgid == p.pgid and os.path.basename(q.command.split()[0]) in ("claude", "zsh", "bash", "sh")
                 for q in procs.values())  # fmt: skip
    send = (lambda sig: os.kill(p.pid, sig)) if shared else (lambda sig: os.killpg(p.pgid, sig))
    try:
        send(signal.SIGTERM)
        time.sleep(3)
        os.kill(p.pid, 0)
        send(signal.SIGKILL)
    except ProcessLookupError:
        pass


def reap(repo: str, dry_run: bool = False, out=sys.stdout) -> int:
    """Kill `repo`'s orphaned gates; returns how many were (or would be) killed."""
    procs = snapshot()
    live = candidates(procs, repo)
    print(f"scope: {os.path.realpath(repo)}", file=out)
    for p in sorted(live, key=lambda p: -p.age):
        print(f"live: pid {p.pid} {program(p.command)} age {p.age // 60}m owner "
              f"{'claude ' + str(p.owner) if p.owner else 'none (orphan)'} cwd {p.cwd}", file=out)  # fmt: skip
    agent = running_agent(time.time())
    if agent:
        print(f"a subagent wrote {agent.name} in the last {AGENT_QUIET}s; reaping nothing", file=out)
        return 0
    killed = 0
    for p in live:
        if p.age < GRACE:
            continue
        verb = "would kill" if dry_run else "killed"
        print(f"{verb}: {p.command[:100]} | age {p.age // 60}m{p.age % 60}s | cwd {p.cwd}", file=out)
        if not dry_run:
            kill_group(p, procs)
        killed += 1
    return killed
