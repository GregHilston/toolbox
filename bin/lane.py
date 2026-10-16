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
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PASS_LINE = re.compile(r"^PASS (\d+) tests\b")
ISSUE_REF = re.compile(r"\(#(\d+)\)")
CURRENT = re.compile(r"^#\d+ .+")
STOPPED = re.compile(r"^Stopped: .*Branch (\S+?)\.$")
UNION = "progress.md merge=union"


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


def start(repo: Path, lane: str, label: str | None, extra: list[str]) -> str:
    """Clone if missing, bring it to the default branch, start the loop detached."""
    clone = clone_path(repo, lane)
    pid_file = clone / ".overnight" / "lane.pid"
    if pid := pid_alive(pid_file):
        raise LaneError(f"lane {lane} is already running (pid {pid}, {pid_file}); `lane.py stop {lane}` ends it")
    loop = shutil.which("overnight-loop.py")
    if not loop:
        raise LaneError("overnight-loop.py is not on PATH")
    branch = default_branch(repo)
    if not clone.exists():
        run("git", "clone", "-q", run("git", "remote", "get-url", "origin", cwd=repo), str(clone))
    if tracker := run("git", "config", "wayfinder.tracker", cwd=repo, check=False):
        run("git", "config", "wayfinder.tracker", tracker, cwd=clone)
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
    return f"started lane {lane} (label {label or lane}), pid {proc.pid}, log {log}"


def lane_row(clone: Path, lane: str) -> list[str]:
    """One status row: lane, state, current issue, done, parked, stopped branch."""
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


def status(repo: Path) -> str:
    """A plain table of every lane clone beside the repo."""
    rows = [["LANE", "STATE", "CURRENT", "DONE", "PARKED", "BRANCH"]]
    for clone in sorted(repo.parent.glob(f"{repo.name}-*")):
        if (clone / ".git").is_dir() and (clone / ".overnight").is_dir():
            rows.append(lane_row(clone, clone.name.removeprefix(f"{repo.name}-")))
    if len(rows) == 1:
        return f"no lanes beside {repo}"
    widths = [max(len(r[i]) for r in rows) for i in range(5)]
    return "\n".join(
        "  ".join(c.ljust(w) for c, w in zip(r[:5], widths)) + ("  " + r[5] if r[5] else "") for r in rows)


def fetch(repo: Path, lane: str, branch: str | None) -> str:
    """Bring a lane's branch into a worktree, rebased onto the default branch."""
    clone = clone_path(repo, lane)
    if not clone.is_dir():
        raise LaneError(f"no clone at {clone}; start the lane first")
    if not branch:
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
    return f"worktree {wt}\nbranch {local} (from {branch})\ncommits {count}\n{state}"


def land(repo: Path, wt: Path, no_verify: bool) -> str:
    """Verify the worktree, fast-forward the default branch, raise the baseline, close issues."""
    wt = wt.resolve()
    if not wt.is_dir():
        raise LaneError(f"worktree {wt} does not exist")
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
        proc = subprocess.run(["./verify.sh"], cwd=wt, capture_output=True, text=True)
        lines = [x for x in (proc.stdout + proc.stderr).splitlines() if x.strip()]
        m = PASS_LINE.match(lines[-1]) if lines else None
        if proc.returncode or not m:
            tail = "\n".join(lines[-5:])
            raise LaneError(f"`./verify.sh` in {wt} did not end in `PASS <n> tests` (exit {proc.returncode}):\n{tail}")
        passed = int(m.group(1))
    subjects = run("git", "log", "--format=%s", f"{base}..{branch}", cwd=repo).splitlines()
    issues = sorted({int(n) for s in subjects for n in ISSUE_REF.findall(s)})
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
    note = f"Merged to main; gate PASS {passed}." if passed is not None else "Merged to main; gate skipped."
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
    sub.add_parser("status", help="one line per lane")
    f = sub.add_parser("fetch", help="bring a lane's branch into a rebased worktree")
    f.add_argument("lane")
    f.add_argument("--branch", help="overnight branch (default: the latest)")
    land_p = sub.add_parser("land", help="verify, fast-forward, raise baseline, close issues")
    land_p.add_argument("worktree", type=Path)
    land_p.add_argument("--no-verify", action="store_true")
    sub.add_parser("stop", help="ask a lane to stop after its current issue").add_argument("lane")
    return p


def main(argv: list[str] | None = None) -> int:
    """Dispatch one subcommand; print its result or its error."""
    args = parser().parse_args(argv)
    try:
        repo = toplevel()
        if args.cmd == "start":
            msg = start(repo, args.lane, args.label, args.extra)
        elif args.cmd == "status":
            msg = status(repo)
        elif args.cmd == "fetch":
            msg = fetch(repo, args.lane, args.branch)
        elif args.cmd == "land":
            msg = land(repo, args.worktree, args.no_verify)
        else:
            msg = stop(repo, args.lane)
    except LaneError as e:
        print(f"lane.py: {e}", file=sys.stderr)
        return 1
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
