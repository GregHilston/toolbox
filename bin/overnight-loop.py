#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Work a repo's GitHub issues unattended, one fresh claude or pi process per issue.

No model runs the loop: this script picks the issue, starts a worker with a clean
context, and lets ./verify.sh, not the worker, decide whether the work stays. A
green issue keeps its commits on an overnight/<time> branch and gets the
overnight:done label; a red one is reset away and gets overnight:parked. Each
issue appends to progress.md, which the next worker reads.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

DONE, PARKED = "overnight:done", "overnight:parked"
PROMPT = """\
You are one worker in an unattended overnight run. Nobody will answer questions.
Implement GitHub issue #{n} in this repository, then stop.

1. Read the issue with `gh issue view {n}`. Read CLAUDE.md, docs/design.md if it
   exists, the titles in docs/adr/, and the end of progress.md.
2. Run ./verify.sh before changing anything, so you know the starting state.
3. Implement only this issue. Turn each checkable line under "Done when" into a
   test that ./verify.sh runs.
4. Run ./verify.sh until it passes. Never edit verify.sh or the issue, and never
   delete or weaken a test to make it pass.
5. Commit with a message ending in "(#{n})". Do not push and do not write to GitHub.

If the issue contradicts an accepted ADR, or you cannot finish, commit nothing
and say why. End with at most three lines: what you did, what is left, and what
the next worker should know.
"""


def sh(*cmd: str, check: bool = True) -> str:
    out = subprocess.run(cmd, capture_output=True, text=True)
    if check and out.returncode:
        sys.exit(f"{' '.join(cmd[:3])} failed: {out.stderr.strip() or out.stdout.strip()}")
    return out.stdout.strip()


def verify(log: Path) -> tuple[bool, str]:
    out = subprocess.run(["./verify.sh"], capture_output=True, text=True)
    text = out.stdout + out.stderr
    with log.open("a") as f:
        f.write(f"\n--- verify.sh exit {out.returncode} ---\n{text}")
    return out.returncode == 0, "\n".join(text.strip().splitlines()[-20:])


def unblocked(n: int, finished: set[int]) -> bool:
    """GitHub's native blocked-by edges; a blocker done tonight counts as closed."""
    out = subprocess.run(["gh", "api", f"repos/{{owner}}/{{repo}}/issues/{n}/dependencies/blocked_by"],
                         capture_output=True, text=True)
    if out.returncode:
        return True  # repo without issue dependencies
    return all(b["state"] == "closed" or b["number"] in finished for b in json.loads(out.stdout))


def next_issue(label: str, tried: set[int], finished: set[int]) -> dict | None:
    issues = json.loads(sh("gh", "issue", "list", "--state", "open", "--label", label,
                           "--limit", "200", "--json", "number,title,labels"))
    for issue in sorted(issues, key=lambda i: i["number"]):
        names = {lab["name"] for lab in issue["labels"]}
        if issue["number"] not in tried and not names & {DONE, PARKED} and unblocked(issue["number"], finished):
            return issue
    return None


def run_worker(args, n: int, log: Path) -> tuple[str, float, bool]:
    """Returns the worker's last message, its cost, and whether it hit a usage limit."""
    prompt = PROMPT.format(n=n)
    if args.harness == "claude":
        cmd = ["claude", "-p", prompt, "--output-format", "json", "--max-turns", "200",
               "--max-budget-usd", str(args.issue_usd),
               "--permission-mode", "bypassPermissions" if args.yolo else "auto"]
    else:
        cmd = ["pi", "-p", "--approve", "--no-session", prompt]
    if args.model:
        cmd[1:1] = ["--model", args.model]
    # 1M-context models otherwise compact only near 967K tokens.
    env = os.environ | {"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "200000"}
    # Own process group, so a Godot server the worker left running dies with it.
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            env=env, start_new_session=True)
    try:
        out, _ = proc.communicate(timeout=args.issue_minutes * 60)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGINT)  # SIGINT lets claude end the turn cleanly
        try:
            out, _ = proc.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            out, _ = proc.communicate()
        out += f"\n(timed out after {args.issue_minutes} min)"
    log.write_text(out)
    if args.harness == "pi":
        return out.strip()[-1500:], 0.0, False
    try:
        result = json.loads(out.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return out.strip()[-1500:], 0.0, False
    text = str(result.get("result", ""))
    limited = bool(result.get("is_error")) and "limit" in text.lower()
    return text[-1500:], float(result.get("total_cost_usd") or 0), limited


def note(n: int, title: str, outcome: str, detail: str) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open("progress.md", "a") as f:
        f.write(f"\n## #{n} {title}: {outcome} ({stamp})\n\n{detail.strip()}\n")
    sh("git", "add", "progress.md")
    sh("git", "commit", "-q", "-m", f"chore(overnight): progress for #{n}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--harness", choices=["claude", "pi"], required=True)
    p.add_argument("--model", help="passed to the harness as --model")
    p.add_argument("--label", default="ready-for-agent", help="issues to work (default ready-for-agent)")
    p.add_argument("--hours", type=float, default=8, help="stop starting issues after this (default 8)")
    p.add_argument("--max-issues", type=int, default=20)
    p.add_argument("--max-fails", type=int, default=3, help="stop after this many parks in a row (default 3)")
    p.add_argument("--issue-minutes", type=int, default=90, help="per-issue time limit (default 90)")
    p.add_argument("--issue-usd", type=float, default=10, help="claude only: per-issue budget (default 10)")
    p.add_argument("--max-cost", type=float, default=60, help="claude only: stop past this total (default 60)")
    p.add_argument("--yolo", action="store_true",
                   help="claude only: bypassPermissions instead of auto; only inside a container or VM")
    args = p.parse_args()

    if not os.access("verify.sh", os.X_OK):
        sys.exit("no executable ./verify.sh here: run this from the repo root, after setting one up")
    if sh("git", "status", "--porcelain"):
        sys.exit("the working tree is not clean: commit or stash first")
    sh("gh", "auth", "status")
    Path(".overnight/logs").mkdir(parents=True, exist_ok=True)
    exclude = Path(sh("git", "rev-parse", "--git-path", "info/exclude"))
    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.touch()
    if ".overnight/" not in exclude.read_text():
        with exclude.open("a") as f:
            f.write("\n.overnight/\n")
    ok, tail = verify(Path(".overnight/logs/baseline.log"))
    if not ok:
        sys.exit(f"./verify.sh fails before any work, so nothing can be judged:\n{tail}")
    for label, colour in ((DONE, "0e8a16"), (PARKED, "d93f0b")):
        sh("gh", "label", "create", label, "--color", colour, "--force")
    branch = "overnight/" + datetime.now().strftime("%Y-%m-%d-%H%M")
    sh("git", "checkout", "-q", "-b", branch)

    deadline = time.time() + args.hours * 3600
    done: dict[int, str] = {}
    parked: dict[int, str] = {}
    tried: set[int] = set()
    cost, fails, why = 0.0, 0, "queue empty"
    while True:
        if Path(".overnight/STOP").exists():
            why = "STOP file"
            break
        if time.time() > deadline:
            why = "out of time"
            break
        if len(tried) >= args.max_issues:
            why = "issue limit"
            break
        if fails >= args.max_fails:
            why = f"{fails} parks in a row"
            break
        if cost >= args.max_cost:
            why = f"cost limit (${cost:.2f})"
            break
        issue = next_issue(args.label, tried, set(done))
        if not issue:
            break
        n, title = issue["number"], issue["title"]
        tried.add(n)
        print(f"#{n} {title}", flush=True)
        base = sh("git", "rev-parse", "HEAD")
        log = Path(f".overnight/logs/{n}.log")
        message, spent, limited = run_worker(args, n, log)
        cost += spent
        if limited:
            sh("git", "reset", "-q", "--hard", base)
            sh("git", "clean", "-qfd")
            why = "usage limit"
            break
        sh("git", "reset", "-q", "--hard", "HEAD")  # keep only what the worker committed
        sh("git", "clean", "-qfd")
        ok, tail = verify(log) if sh("git", "rev-parse", "HEAD") != base else (False, "no commits")
        if ok:
            fails = 0
            done[n] = title
            sh("gh", "issue", "edit", str(n), "--add-label", DONE)
            sh("gh", "issue", "comment", str(n), "--body", f"Done on `{branch}`.\n\n{message}")
            note(n, title, "done", message)
        else:
            fails += 1
            parked[n] = title
            sh("git", "reset", "-q", "--hard", base)
            sh("git", "clean", "-qfd")
            sh("gh", "issue", "edit", str(n), "--add-label", PARKED)
            sh("gh", "issue", "comment", str(n), "--body",
               f"Parked by the overnight run: ./verify.sh did not pass.\n\n{message}\n\n```\n{tail}\n```")
            note(n, title, "parked", f"{message}\n\nverify.sh:\n\n```\n{tail}\n```")
        print(f"  {'done' if ok else 'parked'}" + (f", ${spent:.2f}" if spent else ""), flush=True)

    print(f"\nStopped: {why}. Branch {branch}" + (f", ${cost:.2f} spent." if cost else "."))
    for heading, items in (("Done", done), ("Parked", parked)):
        if items:
            print(f"{heading}:\n" + "\n".join(f"  #{k} {v}" for k, v in items.items()))
    if done:
        closes = " ".join(f"Closes #{k}." for k in done)
        print(f"\nTo review: git push -u origin {branch} && gh pr create --draft --body '{closes}'")


if __name__ == "__main__":
    main()
