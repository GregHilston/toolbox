#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Run overnight-loop.py in parallel lanes and land each finished branch.

A lane is one overnight-loop.py run in its own clone of the repo, working one
GitHub label, so several loops never pick the same issue. Run every command from
the repo's main checkout: clones live beside it as <repo-dir>-<lane>, and `land`
fast-forwards the main checkout's default branch.

Two lanes started in the same minute share a branch name (overnight/<time>), so
`fetch` stores each under its own local name, <lane>-<HHMM>. Every loop commit
appends to progress.md, so `fetch` marks it merge=union before rebasing.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gateslot  # noqa: E402

_spec = importlib.util.spec_from_file_location("session_ctx", Path(__file__).resolve().parent / "session-ctx.py")
session_ctx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(session_ctx)

PASS_LINE = re.compile(r"^PASS (\d+) tests\b")
ISSUE_REF = re.compile(r"\(#(\d+)\)")
CURRENT = re.compile(r"^#\d+ .+")
STOPPED = re.compile(r"^Stopped: .*Branch (\S+?)\.$")
SKIPPED = re.compile(r"^(revert|docs)\b")
GATE_EXIT = re.compile(r"^--- verify\.sh exit (\w+) ---$", re.M)
STOP_WHY = re.compile(r"^Stopped: (.*?)\. Branch ")
SINCE = re.compile(r"^(\d+)([mh])$")
TAIL_BYTES = 400_000
LINE_MAX = 160
POLL_SECONDS = 30
UNION = "progress.md merge=union"
MAX_LANES = 10


class LaneError(Exception):
    """A failure whose message already says what broke."""


def run(*cmd: str, cwd: Path | str | None = None, check: bool = True) -> str:
    """Run one command and return stripped stdout; the seam for git, gh and verify.sh."""
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    except FileNotFoundError as e:
        raise LaneError(f"cannot run `{' '.join(cmd)}`: {e}") from e
    if check and proc.returncode:
        detail = (proc.stderr.strip() or proc.stdout.strip())[-600:]
        raise LaneError(f"`{' '.join(cmd)}` failed (exit {proc.returncode}) in {cwd or '.'}: {detail}")
    return proc.stdout.strip()


def toplevel() -> Path:
    """The main checkout: the cwd's repo root."""
    return Path(run("git", "rev-parse", "--show-toplevel")).resolve()


def default_branch(repo: Path) -> str:
    """origin's default branch, else whatever the checkout has out."""
    ref = run("git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD", cwd=repo, check=False)
    if ref:
        return ref.removeprefix("origin/")
    return run("git", "branch", "--show-current", cwd=repo)


def clone_path(repo: Path, lane: str) -> Path:
    """Where the lane's clone lives."""
    return repo.parent / f"{repo.name}-{lane}"


def pid_alive(pid_file: Path) -> int | None:
    """The pid in the file if that process is still running."""
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
    except (OSError, ValueError):
        return None
    return pid


def lane_clones(repo: Path) -> list[Path]:
    """Every lane clone beside the repo."""
    return [c for c in sorted(repo.parent.glob(f"{repo.name}-*")) if (c / ".git").is_dir() and (c / ".overnight").is_dir()]


def running_count(repo: Path) -> int:
    """Lanes whose loop is alive."""
    return sum(pid_alive(c / ".overnight" / "lane.pid") is not None for c in lane_clones(repo))


def load_line(repo: Path) -> str:
    """The load average and running-lane count, as status and the refusal print them."""
    return f"load {os.getloadavg()[0]:.1f}, {running_count(repo)} lanes running"


def start(repo: Path, lane: str, label: str | None, extra: list[str], force: bool = False,
          max_lanes: int = MAX_LANES, max_load: float | None = None) -> str:
    """Clone if missing, bring it to the default branch, start the loop detached."""
    clone = clone_path(repo, lane)
    pid_file = clone / ".overnight" / "lane.pid"
    if pid := pid_alive(pid_file):
        raise LaneError(f"lane {lane} is already running (pid {pid}, {pid_file}); `lane.py stop {lane}` ends it")
    limit = max_load if max_load is not None else 2 * (os.cpu_count() or 1)
    if not force and (running_count(repo) >= max_lanes or os.getloadavg()[0] > limit):
        raise LaneError(f"not starting lane {lane}: {load_line(repo)} (limits {max_lanes} lanes, load {limit:g}); "
                        "wait for a lane to finish, or pass --force")
    loop = shutil.which("overnight-loop.py")
    if not loop:
        raise LaneError("overnight-loop.py is not on PATH")
    branch = extra[extra.index("--base") + 1] if "--base" in extra[:-1] else default_branch(repo)
    if not clone.exists():
        run("git", "clone", "-q", run("git", "remote", "get-url", "origin", cwd=repo), str(clone))
    if tracker := run("git", "config", "wayfinder.tracker", cwd=repo, check=False):
        run("git", "config", "wayfinder.tracker", tracker, cwd=clone)
    run("git", "fetch", "-q", "origin", cwd=clone)
    run("git", "checkout", "-q", branch, cwd=clone)
    run("git", "pull", "-q", "--ff-only", cwd=clone)
    (clone / ".overnight").mkdir(exist_ok=True)
    exclude = Path(run("git", "rev-parse", "--git-path", "info/exclude", cwd=clone))
    exclude = exclude if exclude.is_absolute() else clone / exclude
    exclude.parent.mkdir(parents=True, exist_ok=True)
    if ".overnight/" not in (exclude.read_text() if exclude.exists() else "").split():
        with exclude.open("a") as f:
            f.write(".overnight/\n")
    log = clone / ".overnight" / "lane.log"
    with log.open("ab") as out:
        proc = subprocess.Popen([loop, "--label", label or lane, *extra], cwd=clone, stdin=subprocess.DEVNULL,
                                stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
    pid_file.write_text(f"{proc.pid}\n")
    (clone / ".overnight" / "lane.label").write_text(f"{label or lane}\n")
    return f"started lane {lane} (label {label or lane}), pid {proc.pid}, log {log}"


def refuse_running(clone: Path, lane: str, force: bool) -> None:
    """A branch taken mid-issue can land work the loop later discards."""
    if not force and (pid := pid_alive(clone / ".overnight" / "lane.pid")):
        raise LaneError(f"lane {lane} is still running (pid {pid}); `lane.py stop {lane}` first, or pass --force")


def stopped_branch(clone: Path) -> str | None:
    """The branch in the lane log's last Stopped line."""
    log = clone / ".overnight" / "lane.log"
    found = None
    for line in (log.read_text(errors="replace").splitlines() if log.exists() else []):
        if m := STOPPED.match(line):
            found = m.group(1)
    return found


def lane_row(clone: Path, lane: str) -> list[str]:
    """One status row: lane, state, current issue, done, parked, stopped branch."""
    if not (clone / ".overnight" / "lane.pid").exists() and not (clone / ".overnight" / "lane.log").exists():
        return [lane, "unknown", "-", "-", "-", ""]
    running = pid_alive(clone / ".overnight" / "lane.pid") is not None
    current, branch, done, parked = "-", "", 0, 0
    log = clone / ".overnight" / "lane.log"
    for line in (log.read_text(errors="replace").splitlines() if log.exists() else []):
        if CURRENT.match(line):
            current = line
        elif line.startswith("  done:"):
            done += 1
        elif line.startswith("  parked:"):
            parked += 1
        elif m := STOPPED.match(line):
            branch = m.group(1)
    return [lane, "running" if running else "stopped", current, str(done), str(parked),
            "" if running else branch]


def context_line(repo: Path) -> str:
    """The orchestrator's context size, or nothing when it has no transcript."""
    path = session_ctx.newest_transcript(repo)
    tokens = session_ctx.context_tokens(path) if path else None
    if tokens is None:
        return ""
    cap = session_ctx.cap()
    return f"orchestrator context {session_ctx.short(tokens)} (cap {session_ctx.short(cap)})" + (" OVER: hand off and /clear" if tokens > cap else "")


def status(repo: Path) -> str:
    """A plain table of every lane clone beside the repo."""
    rows = [["LANE", "STATE", "CURRENT", "DONE", "PARKED", "BRANCH"]]
    for clone in lane_clones(repo):
        rows.append(lane_row(clone, clone.name.removeprefix(f"{repo.name}-")))
    head, foot = load_line(repo), context_line(repo)
    if len(rows) == 1:
        return f"{head}\nno lanes beside {repo}" + (f"\n{foot}" if foot else "")
    widths = [max(len(r[i]) for r in rows) for i in range(5)]
    return head + "\n" + "\n".join(
        "  ".join(c.ljust(w) for c, w in zip(r[:5], widths)) + ("  " + r[5] if r[5] else "") for r in rows) + (f"\n{foot}" if foot else "")


def log_tail(path: Path) -> str:
    """The end of a log; issue logs run to megabytes."""
    try:
        with path.open("rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - TAIL_BYTES))
            return f.read().decode(errors="replace")
    except OSError:
        return ""


def lane_facts(clone: Path) -> dict:
    """What lane.log, lane.pid and the newest commit say about one lane; no network."""
    overnight = clone / ".overnight"
    facts = {"pid": pid_alive(overnight / "lane.pid"), "ticket": "-", "issue": None, "done": 0, "parked": 0,
             "parked_issues": [], "last": "", "why": "", "gate": "-", "gate_runs": 0, "phase": "-", "idle": 0}
    log = overnight / "lane.log"
    for line in (log.read_text(errors="replace").splitlines() if log.exists() else []):
        if CURRENT.match(line):
            facts["ticket"], facts["issue"], facts["last"] = line, int(line[1:].split()[0]), ""
        elif line.startswith("  done:"):
            facts["done"], facts["last"] = facts["done"] + 1, "done"
        elif line.startswith("  parked:"):
            facts["parked"], facts["last"] = facts["parked"] + 1, "parked"
            facts["parked_issues"].append(facts["issue"])
        elif m := STOP_WHY.match(line):
            facts["why"] = m.group(1)
    issue_log = overnight / "logs" / f"{facts['issue']}.log"
    gates = GATE_EXIT.findall(log_tail(issue_log))
    facts["gate_runs"] = len(gates)
    if gates:
        facts["gate"] = "PASS" if gates[-1] == "0" else "FAIL"
    if issue_log.exists():
        facts["idle"] = int((time.time() - issue_log.stat().st_mtime) // 60)
    if facts["pid"]:
        facts["phase"] = ("work", "review", "fix")[min(len(gates), 2)]
    else:
        facts["phase"] = facts["last"] or ("stopped" if facts["why"] else "dead")
    facts["commit"] = run("git", "log", "-1", "--format=%s", cwd=clone, check=False)
    return facts


def minutes(since: str) -> int:
    """30m or 2h as minutes."""
    m = SINCE.match(since)
    if not m:
        raise LaneError(f"--since wants a number and m or h, such as 30m; got {since!r}")
    return int(m.group(1)) * (60 if m.group(2) == "h" else 1)


def digest(repo: Path, since: str | None = None) -> str:
    """One line per lane, plus landings and parks since a time."""
    clones = lane_clones(repo)
    out = [load_line(repo)]
    window = minutes(since) if since else 0
    parks = []
    for clone in clones:
        lane = clone.name.removeprefix(f"{repo.name}-")
        f = lane_facts(clone)
        idle = f" {f['idle']}m idle" if f["pid"] else ""
        reason = f": {f['why']}" if f["why"] and not f["pid"] else ""
        gate = f" gate {f['gate']}" if f["gate"] != "-" else ""
        line = (f"{lane} {f['ticket']} | {f['phase']}{idle}{reason} | pid {f['pid'] or 'dead'} | "
                f"done {f['done']} parked {f['parked']}{gate} | {f['commit']}")
        out.append(line if len(line) <= LINE_MAX else line[:LINE_MAX - 3] + "...")
        for n in f["parked_issues"]:
            logged = clone / ".overnight" / "logs" / f"{n}.log"
            if window and logged.exists() and time.time() - logged.stat().st_mtime < window * 60:
                parks.append(f"{lane} #{n}")
    if window:
        landed = run("git", "log", f"--since={window} minutes ago", "--format=%s", default_branch(repo), cwd=repo)
        out.append(f"landed since {since}: " + ("; ".join(landed.splitlines()) or "none"))
        out.append(f"parked since {since}: " + (", ".join(parks) or "none"))
    return "\n".join(out)


class Watcher:
    """Diffs lane state between polls; lane starts wait for the digest, the rest print at once."""

    def __init__(self, repo: Path, minutes: float, clock=time.monotonic) -> None:
        self.repo, self.window, self.clock = repo, minutes * 60, clock
        self.prev: dict | None = None
        self.starts: list[str] = []
        self.flushed = clock()

    def snapshot(self) -> dict:
        """Lane facts by name, plus the main checkout's newest commit under the key ''."""
        snap = {c.name.removeprefix(f"{self.repo.name}-"): lane_facts(c) for c in lane_clones(self.repo)}
        snap[""] = {"commit": run("git", "log", "-1", "--format=%H %s", cwd=self.repo, check=False)}
        return snap

    def step(self) -> list[str]:
        """Lines to print now."""
        cur, prev = self.snapshot(), self.prev
        self.prev = cur
        if prev is None:
            return []
        now = []
        for lane, f in cur.items():
            old = prev.get(lane)
            if not lane:
                if old and f["commit"] != old["commit"]:
                    now.append(f"landed: {f['commit'].partition(' ')[2]}")
                continue
            if f["pid"] and (not old or not old["pid"] or old["issue"] != f["issue"]):
                self.starts.append(f"{lane} started {f['ticket']}")
            if not old:
                continue
            if old["pid"] and not f["pid"]:
                now.append(f"lane {lane} stopped: {f['why'] or 'no Stopped line, it died'}")
            if f["parked"] > old["parked"]:
                now.append(f"lane {lane} parked #{f['parked_issues'][-1]}")
            if f["gate"] == "FAIL" and (f["issue"], f["gate_runs"]) != (old["issue"], old["gate_runs"]):
                now.append(f"lane {lane} gate FAIL on #{f['issue']}")
        if self.clock() - self.flushed >= self.window:
            self.flushed = self.clock()
            if self.starts:
                now.append("lane starts:\n  " + "\n  ".join(self.starts))
                self.starts = []
        return now


def watch(repo: Path, minutes: float) -> None:
    """Print a lane event at once, or batched into a digest, until interrupted."""
    watcher = Watcher(repo, minutes)
    try:
        while True:
            for line in watcher.step():
                print(line, flush=True)
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        if watcher.starts:
            print("lane starts:\n  " + "\n  ".join(watcher.starts), flush=True)


def fetch(repo: Path, lane: str, branch: str | None, force: bool = False) -> str:
    """Bring a lane's branch into a worktree, rebased onto the default branch."""
    clone = clone_path(repo, lane)
    if not clone.is_dir():
        raise LaneError(f"no clone at {clone}; start the lane first")
    refuse_running(clone, lane, force)
    warning = ""
    if not branch:
        branch = stopped_branch(clone)
    if not branch:
        warning = f"warning: {clone}/.overnight/lane.log names no stopped branch; took the newest overnight/* branch\n"
        found = run("git", "branch", "--list", "overnight/*", "--format=%(refname:short)", cwd=clone).split()
        if not found:
            raise LaneError(f"no overnight/* branch in {clone}")
        branch = sorted(found)[-1]
    local = f"{lane}-{branch.rsplit('-', 1)[-1]}"
    taken = set(run("git", "branch", "--format=%(refname:short)", cwd=repo).split())
    base, n = local, 1
    while local in taken:
        n += 1
        local = f"{base}-{n}"
    base_branch = default_branch(repo)
    run("git", "fetch", "-q", str(clone), f"refs/heads/{branch}:refs/heads/{local}", cwd=repo)
    wt = repo.parent / f"{repo.name}-wt-{lane}"
    run("git", "worktree", "add", "-q", str(wt), local, cwd=repo)
    attrs = Path(run("git", "rev-parse", "--path-format=absolute", "--git-common-dir", cwd=repo)) / "info" / "attributes"
    attrs.parent.mkdir(parents=True, exist_ok=True)
    if UNION not in (attrs.read_text() if attrs.exists() else "").splitlines():
        with attrs.open("a") as f:
            f.write(UNION + "\n")
    rebase = subprocess.run(["git", "rebase", base_branch], cwd=wt, capture_output=True, text=True)
    count = run("git", "rev-list", "--count", f"{base_branch}..{local}", cwd=repo)
    if rebase.returncode:
        files = run("git", "diff", "--name-only", "--diff-filter=U", cwd=wt).splitlines()
        if not files:
            raise LaneError(f"`git rebase {base_branch}` failed in {wt}: {rebase.stderr.strip()[-600:]}")
        state = "conflicts, rebase left stopped in the worktree:\n" + "\n".join(f"  {f}" for f in files)
    else:
        state = "clean"
    return f"{warning}worktree {wt}\nbranch {local} (from {branch})\ncommits {count}\n{state}"


def land(repo: Path, wt: Path, no_verify: bool, force: bool = False) -> str:
    """Verify the worktree, fast-forward the default branch, raise the baseline, close issues."""
    wt = wt.resolve()
    if not wt.is_dir():
        raise LaneError(f"worktree {wt} does not exist")
    if run("git", "status", "--porcelain", "--untracked-files=no", cwd=repo):
        raise LaneError(f"the main checkout {repo} has uncommitted changes; commit or stash them first")
    lane = wt.name.removeprefix(f"{repo.name}-wt-")
    clone = clone_path(repo, lane)
    refuse_running(clone, lane, force)
    branch = run("git", "branch", "--show-current", cwd=wt)
    if not branch:
        raise LaneError(f"{wt} has no branch checked out (rebase in progress?)")
    base = default_branch(repo)
    if run("git", "branch", "--show-current", cwd=repo) != base:
        raise LaneError(f"the main checkout {repo} is not on {base}")
    if subprocess.run(["git", "merge-base", "--is-ancestor", base, branch], cwd=repo).returncode:
        raise LaneError(f"{branch} is not a fast-forward of {base}; rebase it in {wt} first")
    passed = None
    if not no_verify:
        with gateslot.slot(land=True):
            proc = subprocess.run(["./verify.sh"], cwd=wt, capture_output=True, text=True)
        lines = [x for x in (proc.stdout + proc.stderr).splitlines() if x.strip()]
        m = PASS_LINE.match(lines[-1]) if lines else None
        if proc.returncode or not m:
            tail = "\n".join(lines[-5:])
            raise LaneError(f"`./verify.sh` in {wt} did not end in `PASS <n> tests` (exit {proc.returncode}):\n{tail}")
        passed = int(m.group(1))
        floor = repo / "tests" / "baseline_count"
        if floor.exists() and passed < int(floor.read_text().strip() or 0):
            raise LaneError(f"`./verify.sh` in {wt} passed {passed} tests, below tests/baseline_count "
                            f"{floor.read_text().strip()}: tests were dropped")
    subjects = run("git", "log", "--format=%s", f"{base}..{branch}", cwd=repo).splitlines()
    wanted = sorted({int(n) for s in subjects if not SKIPPED.match(s) for n in ISSUE_REF.findall(s)})
    label_file = clone / ".overnight" / "lane.label"
    label = label_file.read_text().strip() if label_file.exists() else lane
    out = [f"verify: {'skipped' if passed is None else f'PASS {passed} tests'}"]
    run("git", "merge", "-q", "--ff-only", branch, cwd=repo)
    out.append(f"fast-forwarded {base} to {branch} ({len(subjects)} commits)")
    baseline = repo / "tests" / "baseline_count"
    if passed is not None and baseline.exists() and passed > int(baseline.read_text().strip() or 0):
        baseline.write_text(f"{passed}\n")
        run("git", "add", "tests/baseline_count", cwd=repo)
        run("git", "commit", "-q", "-m", f"chore: raise the test baseline to {passed}", cwd=repo)
        out.append(f"raised tests/baseline_count to {passed}")
    run("git", "push", "-q", cwd=repo)
    out.append(f"pushed {base}")
    if passed is not None:
        gateslot.mark_passed(repo)  # only the baseline count changed since
    note =f"Merged to main; gate PASS {passed}." if passed is not None else "Merged to main; gate skipped."
    issues = []
    for n in wanted:
        info = json.loads(run("gh", "issue", "view", str(n), "--json", "labels,state", cwd=repo))
        if info["state"] == "OPEN" and label in [x["name"] for x in info["labels"]]:
            issues.append(n)
    for n in issues:
        run("gh", "issue", "close", str(n), "--comment", note, cwd=repo)
    out.append("closed " + (", ".join(f"#{n}" for n in issues) or "no issues"))
    run("git", "worktree", "remove", "--force", str(wt), cwd=repo)
    run("git", "branch", "-d", branch, cwd=repo)
    out.append(f"removed worktree {wt} and branch {branch}")
    return "\n".join(out)


def stop(repo: Path, lane: str) -> str:
    """Ask the lane's loop to end after its current issue."""
    clone = clone_path(repo, lane)
    if not clone.is_dir():
        raise LaneError(f"no clone at {clone}")
    flag = clone / ".overnight" / "STOP"
    flag.parent.mkdir(exist_ok=True)
    flag.touch()
    return f"touched {flag}; lane {lane} stops after its current issue"


def parser() -> argparse.ArgumentParser:
    """The command line."""
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start", help="clone if missing, start the loop detached")
    s.add_argument("lane")
    s.add_argument("--label", help="issue label to work (default: the lane name)")
    s.add_argument("extra", nargs="*", help="after --: arguments for overnight-loop.py")
    s.add_argument("--max-lanes", type=int, default=MAX_LANES, help="refuse at this many running lanes (default 10)")
    s.add_argument("--max-load", type=float, help="refuse above this 1-minute load average (default 2 x cores)")
    s.add_argument("--force", action="store_true", help="start despite the lane count or load")
    d = sub.add_parser("digest", help="one line per lane, from lane files and git log only")
    d.add_argument("--since", help="also list landings and parks in this window, such as 30m or 2h")
    w = sub.add_parser("watch", help="print stops, parks, landings and gate failures; batch lane starts")
    w.add_argument("--digest", type=float, default=20, metavar="MINUTES", help="minutes between start digests (20)")
    sub.add_parser("status", help="load and lane count, then one line per lane")
    f = sub.add_parser("fetch", help="bring a lane's branch into a rebased worktree")
    f.add_argument("lane")
    f.add_argument("--branch", help="overnight branch (default: the one the lane log says it stopped on)")
    f.add_argument("--force", action="store_true", help="even while the lane's loop runs")
    land_p = sub.add_parser("land", help="verify, fast-forward, raise baseline, close issues")
    land_p.add_argument("worktree", type=Path)
    land_p.add_argument("--no-verify", action="store_true")
    land_p.add_argument("--force", action="store_true", help="even while the lane's loop runs")
    sub.add_parser("stop", help="ask a lane to stop after its current issue").add_argument("lane")
    return p


def main(argv: list[str] | None = None) -> int:
    """Dispatch one subcommand; print its result or its error."""
    args = parser().parse_args(argv)
    try:
        repo = toplevel()
        if args.cmd == "start":
            msg = start(repo, args.lane, args.label, args.extra, args.force, args.max_lanes, args.max_load)
        elif args.cmd == "status":
            msg = status(repo)
        elif args.cmd == "digest":
            msg = digest(repo, args.since)
        elif args.cmd == "watch":
            watch(repo, args.digest)
            return 0
        elif args.cmd == "fetch":
            msg = fetch(repo, args.lane, args.branch, args.force)
        elif args.cmd == "land":
            msg = land(repo, args.worktree, args.no_verify, args.force)
        else:
            msg = stop(repo, args.lane)
    except LaneError as e:
        print(f"lane.py: {e}", file=sys.stderr)
        return 1
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
