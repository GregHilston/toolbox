#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Work a repo's GitHub issues unattended, one fresh claude or pi process per issue.

No model runs the loop: this script picks the issue, starts a worker with a clean
context, and lets ./verify.sh, not the worker, decide whether the work stays. A
reviewer from another model family plans each issue and reviews green work, with
one fix pass when it asks for changes. Kept work stays on an overnight/<time>
branch labelled overnight:done; the rest is reset away and labelled
overnight:parked. Each issue appends to progress.md, which the next worker reads.

--budget sends pi workers through the LiteLLM gateway's `cloud` model and stops
starting issues once this run has spent that much there. The gateway's own daily
cap on `cloud` is the hard limit underneath: past it, every request gets a 429.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("preflight", HERE / "deepseek-preflight.py")
preflight = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(preflight)

DONE, PARKED, WORKING = "overnight:done", "overnight:parked", "overnight:working"
GATEWAY = os.environ.get("LITELLM_URL", "https://llm.grehg2.xyz")
OUT_OF_MONEY = re.compile(r"Budget has been exceeded|budget_exceeded|Exceeded budget|Insufficient Balance")

WORKER = """\
You are one worker in an unattended overnight run. Nobody will answer questions.
Implement GitHub issue #{n} in this repository, then stop.

1. Read the issue with `gh issue view {n}`. Read CLAUDE.md, docs/design.md if it
   exists, the titles in docs/adr/, and the end of progress.md.
2. Run ./verify.sh before changing anything, so you know the starting state.
3. Implement only this issue. Turn each checkable line under "Done when" into a
   test that ./verify.sh runs.
4. Run ./verify.sh until it passes. Never edit verify.sh or the issue, and never
   delete or weaken a test to make it pass.
5. Commit with a conventional commit message ending in "(#{n})", such as
   "feat(car): add handbrake (#{n})". Do not push and do not write to GitHub.

If the issue contradicts an accepted ADR, or you cannot finish, commit nothing
and say why. End with at most three lines: what you did, what is left, and what
the next worker should know.
"""
PLAN = """\
Plan the implementation of this GitHub issue for another agent, who will do the
work. Read CLAUDE.md and the code the issue touches; do not edit anything.
Reply with a short plan: the files to change, the test for each "Done when"
line, and the risks.

{issue}
"""
REVIEW = """\
Review this change for GitHub issue #{n}. Read CLAUDE.md and any file you need;
do not edit anything. Check that every checkable "Done when" line has a test
that would fail without the change, that the code follows CLAUDE.md, and that
no test was weakened or deleted. List each required change. End with exactly
one line, either "VERDICT: approve" or "VERDICT: changes".

{issue}

The diff:

{diff}
"""
FIX = """\
A reviewer asked for changes to the work already committed on this branch:

{findings}

Make them, run ./verify.sh until it passes, and commit.
"""


def sh(*cmd: str, check: bool = True) -> str:
    out = subprocess.run(cmd, capture_output=True, text=True)
    if check and out.returncode:
        sys.exit(f"{' '.join(cmd[:3])} failed: {out.stderr.strip() or out.stdout.strip()}")
    return out.stdout.strip()


def cloud_spend() -> float:
    """What the gateway has counted against DeepSeek in its current daily window."""
    key = os.environ.get("LITELLM_API_KEY")
    if not key:  # pi's config already holds the gateway key
        models = json.loads((Path.home() / ".pi/agent/models.json").read_text())
        key = models["providers"]["litellm"]["apiKey"]
    req = urllib.request.Request(GATEWAY + "/provider/budgets", headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return float(json.load(r)["providers"]["deepseek"]["spend"])


class RunSpend:
    """This run's share of the gateway's counter, which resets once a day."""

    def __init__(self) -> None:
        self.last = cloud_spend()
        self.total = 0.0

    def read(self) -> float:
        now = cloud_spend()
        self.total += now - self.last if now >= self.last else now
        self.last = now
        return self.total


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


def pi_result(out: str) -> tuple[str, float]:
    """The last assistant text, and the cost priced from DeepSeek's table.

    pi's own cost object uses a stale catalog and under-reports about 3x.
    """
    text, cost = "", 0.0
    for line in out.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = event.get("message") or {}
        if event.get("type") != "message_end" or msg.get("role") != "assistant":
            continue
        text = "".join(b.get("text", "") for b in msg.get("content", []) if b.get("type") == "text") or text
        when = datetime.fromtimestamp(msg.get("timestamp", time.time() * 1000) / 1000, timezone.utc)
        cost += preflight.turn_cost(msg.get("model"), msg.get("usage") or {}, when)
    return text, cost


def run_agent(args, harness: str, model: str | None, prompt: str, log: Path,
              read_only: bool = False) -> tuple[str, float, bool]:
    """Returns the agent's last message, its cost, and whether money ran out."""
    if harness == "claude":
        cmd = ["claude", "-p", prompt, "--output-format", "json", "--max-turns", "200",
               "--max-budget-usd", str(args.issue_usd)]
        if read_only:
            cmd += ["--permission-mode", "dontAsk", "--allowedTools", "Read", "Grep", "Glob"]
        else:
            cmd += ["--permission-mode", "bypassPermissions" if args.yolo else "auto"]
    else:
        # Disabled mode still blocks catastrophes but lets workers commit.
        cmd = ["pi", "-p", "--approve", "--no-session", "--mode", "json", "--bash-guard-disabled"]
        if read_only:
            cmd += ["--tools", "read,grep,find,ls"]
        if args.budget:
            cmd += ["--provider", "litellm"]
            model = "cloud"
        cmd += ["--", prompt]
    if model:
        cmd[1:1] = ["--model", model]
    # 1M-context models otherwise compact only near 967K tokens.
    env = os.environ | {"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "200000"}
    # Own process group, so a Godot server the worker left running dies with it.
    # stdin=DEVNULL: pi reads a piped stdin to EOF before anything else.
    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, env=env, start_new_session=True)
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
    with log.open("a") as f:
        f.write(out)
    broke = bool(OUT_OF_MONEY.search(out))
    if harness == "pi":
        text, cost = pi_result(out)
        return text[-1500:], cost, broke
    try:
        result = json.loads(out.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return out.strip()[-1500:], 0.0, broke
    text = str(result.get("result", ""))
    limited = bool(result.get("is_error")) and "limit" in text.lower()
    return text[-1500:], float(result.get("total_cost_usd") or 0), broke or limited


def tidy(to: str = "HEAD") -> None:
    sh("git", "reset", "-q", "--hard", to)
    sh("git", "clean", "-qfd")


def note(n: int, title: str, outcome: str, detail: str) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open("progress.md", "a") as f:
        f.write(f"\n## #{n} {title}: {outcome} ({stamp})\n\n{detail.strip()}\n")
    sh("git", "add", "progress.md")
    sh("git", "commit", "-q", "-m", f"chore(overnight): progress for #{n}")


def board(args) -> None:
    if args.board:
        out = subprocess.run([str(HERE / "board-sync.py"), "--project", str(args.board)],
                             capture_output=True, text=True)
        if out.returncode:
            print(f"  board sync failed: {out.stderr.strip()}", flush=True)


def stop_reason(args, tried: set[int], fails: int, cost: float, deadline: float) -> str | None:
    now = datetime.now(timezone.utc)
    if Path(".overnight/STOP").exists():
        return "STOP file"
    if time.time() > deadline:
        return "out of time"
    if args.off_peak and preflight.minutes_until_peak(now) is not None \
            and preflight.minutes_until_peak(now) < args.off_peak_margin:
        return "off-peak window ending"
    if len(tried) >= args.max_issues:
        return "issue limit"
    if fails >= args.max_fails:
        return f"{fails} parks in a row"
    if args.spend:
        spent = args.spend.read()
        if spent >= args.budget - 0.05:
            return f"budget (${spent:.2f} of ${args.budget:.2f})"
    elif cost >= args.max_cost:
        return f"cost limit (${cost:.2f})"
    return None


def work_issue(args, n: int, title: str, branch: str) -> tuple[bool, float, bool]:
    """Plan, build, verify, review and maybe fix one issue. Returns kept, cost, out of money."""
    log = Path(f".overnight/logs/{n}.log")
    issue = sh("gh", "issue", "view", str(n))
    base = sh("git", "rev-parse", "HEAD")
    cost, plan = 0.0, ""
    if args.reviewer != "none":
        plan, spent, broke = run_agent(args, args.reviewer, args.reviewer_model, PLAN.format(issue=issue),
                                       log, read_only=True)
        cost += spent
        tidy()
        if broke:
            return False, cost, True
    prompt = WORKER.format(n=n) + (f"\nA planner suggests:\n\n{plan}\n" if plan else "")
    message, spent, broke = run_agent(args, args.harness, args.model, prompt, log)
    cost += spent
    if broke:
        tidy(base)
        return False, cost, True
    tidy()  # keep only what the worker committed
    ok, tail = verify(log) if sh("git", "rev-parse", "HEAD") != base else (False, "no commits")
    if ok and args.reviewer != "none":
        diff = sh("git", "diff", f"{base}..HEAD")[:60000]
        review, spent, broke = run_agent(args, args.reviewer, args.reviewer_model,
                                         REVIEW.format(n=n, issue=issue, diff=diff), log, read_only=True)
        cost += spent
        tidy()
        if not broke and review.strip().endswith("VERDICT: changes"):
            message, spent, broke = run_agent(args, args.harness, args.model,
                                              WORKER.format(n=n) + "\n" + FIX.format(findings=review), log)
            cost += spent
            tidy()
            ok, tail = verify(log)
            message += "\n\nAfter review:\n" + review[-800:]
        if broke:
            tidy(base)
            return False, cost, True
    if ok:
        sh("gh", "issue", "edit", str(n), "--add-label", DONE, "--remove-label", WORKING)
        sh("gh", "issue", "comment", str(n), "--body", f"Done on `{branch}`.\n\n{message}")
        note(n, title, "done", message)
    else:
        tidy(base)
        sh("gh", "issue", "edit", str(n), "--add-label", PARKED, "--remove-label", WORKING)
        sh("gh", "issue", "comment", str(n), "--body",
           f"Parked by the overnight run: ./verify.sh did not pass.\n\n{message}\n\n```\n{tail}\n```")
        note(n, title, "parked", f"{message}\n\nverify.sh:\n\n```\n{tail}\n```")
    return ok, cost, False


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--harness", choices=["claude", "pi"], required=True, help="runs the workers")
    p.add_argument("--model", help="the workers' model, passed to the harness as --model")
    p.add_argument("--reviewer", choices=["claude", "pi", "none"], default="claude",
                   help="plans each issue and reviews green work (default claude)")
    p.add_argument("--reviewer-model")
    p.add_argument("--label", default="ready-for-agent", help="issues to work (default ready-for-agent)")
    p.add_argument("--hours", type=float, default=8, help="stop starting issues after this (default 8)")
    p.add_argument("--max-issues", type=int, default=20)
    p.add_argument("--max-fails", type=int, default=3, help="stop after this many parks in a row (default 3)")
    p.add_argument("--issue-minutes", type=int, default=90, help="time limit per agent run (default 90)")
    p.add_argument("--issue-usd", type=float, default=10, help="claude only: budget per agent run (default 10)")
    p.add_argument("--max-cost", type=float, default=60,
                   help="stop past this total (default 60); pi is priced from DeepSeek's table")
    p.add_argument("--budget", type=float,
                   help="pi only: dollars this run may spend on the gateway's `cloud` model")
    p.add_argument("--off-peak", action="store_true",
                   help="wait for DeepSeek's off-peak hours and stop before peak; weekends are all off-peak")
    p.add_argument("--off-peak-margin", type=int, default=20,
                   help="minutes before peak to stop starting issues (default 20)")
    p.add_argument("--board", type=int, help="GitHub project number to keep in sync with board-sync.py")
    p.add_argument("--yolo", action="store_true",
                   help="claude workers: bypassPermissions instead of auto; only inside a container or VM")
    args = p.parse_args()
    args.spend = None

    if not os.access("verify.sh", os.X_OK):
        sys.exit("no executable ./verify.sh here: run this from the repo root, after setting one up")
    if sh("git", "status", "--porcelain"):
        sys.exit("the working tree is not clean: commit or stash first")
    if args.budget and args.harness != "pi":
        sys.exit("--budget routes pi workers through LiteLLM; it does not cover claude workers")
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
    for label, colour in ((DONE, "0e8a16"), (PARKED, "d93f0b"), (WORKING, "5319e7")):
        sh("gh", "label", "create", label, "--color", colour, "--force")
    for stale in json.loads(sh("gh", "issue", "list", "--label", WORKING, "--json", "number")):
        sh("gh", "issue", "edit", str(stale["number"]), "--remove-label", WORKING)

    if args.off_peak:
        while preflight.is_peak(datetime.now(timezone.utc)):
            print("Peak hours: waiting for the off-peak window.", flush=True)
            time.sleep(300)
    deadline = time.time() + args.hours * 3600
    branch = "overnight/" + datetime.now().strftime("%Y-%m-%d-%H%M")
    sh("git", "checkout", "-q", "-b", branch)
    if args.budget:
        try:
            args.spend = RunSpend()
        except (OSError, KeyError) as e:
            sys.exit(f"could not read the gateway's spend at {GATEWAY}/provider/budgets: {e}")
    board(args)

    done: dict[int, str] = {}
    parked: dict[int, str] = {}
    tried: set[int] = set()
    cost, fails = 0.0, 0
    try:
        while not (why := stop_reason(args, tried, fails, cost, deadline)):
            issue = next_issue(args.label, tried, set(done))
            if not issue:
                why = "queue empty"
                break
            n, title = issue["number"], issue["title"]
            tried.add(n)
            print(f"#{n} {title}", flush=True)
            sh("gh", "issue", "edit", str(n), "--add-label", WORKING)
            board(args)
            kept, spent, broke = work_issue(args, n, title, branch)
            cost += spent
            if broke:
                sh("gh", "issue", "edit", str(n), "--remove-label", WORKING)
                why = "out of money"
                break
            (done if kept else parked)[n] = title
            fails = 0 if kept else fails + 1
            print(f"  {'done' if kept else 'parked'}, ${spent:.2f}", flush=True)
            board(args)
    finally:
        if args.spend:
            cost = args.spend.read()
        board(args)

    print(f"\nStopped: {why}. Branch {branch}, ${cost:.2f} spent.")
    for heading, items in (("Done", done), ("Parked", parked)):
        if items:
            print(f"{heading}:\n" + "\n".join(f"  #{k} {v}" for k, v in items.items()))
    if done:
        closes = " ".join(f"Closes #{k}." for k in done)
        print(f"\nTo review: git push -u origin {branch} && gh pr create --draft --body '{closes}'")


if __name__ == "__main__":
    main()
