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

pi workers use the LiteLLM gateway's `cloud` model unless --model names another.
--budget stops starting issues once this run has spent that much there. The gateway's own daily
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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("preflight", HERE / "deepseek-preflight.py")
preflight = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(preflight)

DONE, PARKED, WORKING = "overnight:done", "overnight:parked", "overnight:working"
GATEWAY = os.environ.get("LITELLM_URL", "https://llm.grehg2.xyz")
# Headless, Greg's pi config turns `write: ask` into a refusal, so each repo
# gets a git-excluded override that pi loads under --approve.
PI_OVERRIDE = Path(".pi/extensions/pi-permission-system/config.json")
# A worker that loosens the gate would pass it, so changing one parks the issue.
GATE = ("verify.sh", "tests/baseline_count")
OUT_OF_MONEY = re.compile(r"Budget has been exceeded|budget_exceeded|Exceeded budget|Insufficient Balance"
                          r"|usage limit|hit your limit|Credit balance is too low", re.I)

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
PING = "Reply with the word ok and nothing else."
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


def signal_group(pgid: int, sig: int) -> None:
    try:
        os.killpg(pgid, sig)
    except ProcessLookupError:
        pass


def run_group(cmd: list[str], minutes: float, stop: int = signal.SIGINT, **popen) -> int | None:
    """Run cmd in a process group of its own; None means it timed out.

    Output goes to files, not pipes: a leftover child holding a pipe open would
    keep a wait on EOF hanging after cmd itself has exited.
    """
    proc = subprocess.Popen(cmd, start_new_session=True, **popen)
    try:
        return proc.wait(timeout=minutes * 60)
    except subprocess.TimeoutExpired:
        signal_group(proc.pid, stop)
        try:
            proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            pass
        return None
    finally:
        signal_group(proc.pid, signal.SIGKILL)
        proc.wait()


def verify(args, log: Path) -> tuple[bool, str]:
    out = Path(".overnight/verify.out")
    with out.open("w") as f:
        code = run_group(["./verify.sh"], args.verify_minutes, signal.SIGKILL,
                         stdin=subprocess.DEVNULL, stdout=f, stderr=subprocess.STDOUT)
    text = out.read_text(errors="replace")
    if code is None:
        text += f"\n./verify.sh timed out after {args.verify_minutes:g} min"
    with log.open("a") as f:
        f.write(f"\n--- verify.sh exit {code} ---\n{text}")
    return code == 0, "\n".join(text.strip().splitlines()[-20:])


def verdict(review: str) -> str | None:
    """The review's last verdict, read through markdown emphasis and punctuation."""
    found = re.findall(r"VERDICT\W*(approve|changes)\b", review, re.I)
    return found[-1].lower() if found else None


def check(args, base: str, branch: str, log: Path) -> tuple[bool, str]:
    """Judge what was committed on branch since base."""
    if (left := sh("git", "branch", "--show-current")) != branch:
        sh("git", "checkout", "-qf", branch)
        return False, f"the worker moved off {branch} to {left or 'a detached HEAD'}"
    if sh("git", "rev-parse", "HEAD") == base:
        return False, "no commits"
    if changed := sh("git", "diff", "--name-only", base, "HEAD", "--", *GATE).split():
        return False, f"the worker changed {', '.join(changed)}, which only a human may change"
    return verify(args, log)


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


@dataclass
class Run:
    """One agent run: its last message, its cost, and the error it ended on."""

    text: str = ""
    cost: float = 0.0
    error: str = ""

    @property
    def broke(self) -> bool:
        # Only the error, never the whole stream: tool output quotes issues.
        return bool(OUT_OF_MONEY.search(self.error))


def pi_result(out: str) -> Run:
    """Priced from DeepSeek's table: pi's own cost object under-reports about 3x."""
    run = Run()
    for line in out.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "auto_retry_end" and event.get("finalError"):
            run.error = str(event["finalError"])
        msg = event.get("message") or {}
        if event.get("type") != "message_end" or msg.get("role") != "assistant":
            continue
        run.text = "".join(b.get("text", "") for b in msg.get("content", []) if b.get("type") == "text") or run.text
        if msg.get("stopReason") == "error":
            run.error = str(msg.get("errorMessage", "error"))
        when = datetime.fromtimestamp(msg.get("timestamp", time.time() * 1000) / 1000, timezone.utc)
        run.cost += preflight.turn_cost(msg.get("model"), msg.get("usage") or {}, when)
    return run


def run_agent(args, harness: str, model: str | None, prompt: str, log: Path,
              read_only: bool = False) -> Run:
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
        if model in (None, "cloud"):
            cmd += ["--provider", "litellm"]
            model = "cloud"
        cmd += ["--", prompt]
    if model:
        cmd[1:1] = ["--model", model]
    # 1M-context models otherwise compact only near 967K tokens.
    env = os.environ | {"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "200000"}
    stdout = Path(".overnight/agent.out")
    # stdin=DEVNULL: pi reads a piped stdin to EOF before anything else.
    # SIGINT on timeout lets claude end the turn and print its result.
    with stdout.open("w") as out, log.open("a") as err:
        code = run_group(cmd, args.issue_minutes, signal.SIGINT, stdin=subprocess.DEVNULL,
                         stdout=out, stderr=err, env=env)
    out = stdout.read_text(errors="replace")
    with log.open("a") as f:
        f.write(out + (f"\n(timed out after {args.issue_minutes:g} min)\n" if code is None else ""))
    if harness == "pi":
        run = pi_result(out)
        run.text = run.text[-1500:]
        return run
    return claude_result(out)


def claude_result(out: str) -> Run:
    for line in reversed(out.splitlines()):
        try:
            result = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(result, dict) and result.get("type") == "result":
            text = str(result.get("result", ""))
            return Run(text[-1500:], float(result.get("total_cost_usd") or 0), text if result.get("is_error") else "")
    return Run(out.strip()[-1500:], error="claude printed no result")


def smoke_test(args, harness: str, model: str | None) -> None:
    """One turn before touching anything, so a bad model or key fails here, not as a park per issue."""
    log = Path(".overnight/logs/startup.log")
    run = run_agent(args, harness, model, PING, log, read_only=True)
    if run.error or not run.text.strip():
        name = f"{harness} --model {model}" if model else harness
        sys.exit(f"{name} could not answer a one-line prompt: {run.error or 'no reply'}. See {log}.")


def allow_pi_writes() -> None:
    if not subprocess.run(["git", "ls-files", "--error-unmatch", str(PI_OVERRIDE)], capture_output=True).returncode:
        print(f"Using the repo's own {PI_OVERRIDE}: pi workers can write only where it allows.", flush=True)
    elif not PI_OVERRIDE.exists():
        PI_OVERRIDE.parent.mkdir(parents=True, exist_ok=True)
        PI_OVERRIDE.write_text(json.dumps({"permission": {"write": {"*": "allow"}}}) + "\n")


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


def peak_soon(now: datetime, margin: int) -> bool:
    """Peak now, or too close to it to start an issue that would run into it."""
    return preflight.is_peak(now) or preflight.minutes_until_peak(now) < margin


def stop_reason(args, tried: set[int], fails: int, cost: float, deadline: float) -> str | None:
    if Path(".overnight/STOP").exists():
        return "STOP file"
    if time.time() > deadline:
        return "out of time"
    if len(tried) >= args.max_issues:
        return "issue limit"
    if fails >= args.max_fails:
        return f"{fails} parks in a row"
    if args.spend:
        spent = args.spend.read()
        if spent >= args.budget - 0.05:
            return f"budget (${spent:.2f} of ${args.budget:.2f})"
    if cost >= args.max_cost:
        return f"cost limit (${cost:.2f})"
    return None


def drop_reviewer(args, n: int, error: str) -> None:
    """A reviewer out of money should not end a night the workers can still fund."""
    print(f"  the {args.reviewer} reviewer stopped ({error[:200]}); the rest of the run goes unreviewed", flush=True)
    args.reviewer, args.unreviewed_from = "none", n


def work_issue(args, n: int, title: str, branch: str) -> tuple[str | None, float, bool]:
    """Plan, build, verify, review and maybe fix one issue.

    Returns "done", "parked" or None (left as it was), the cost, and whether
    money ran out.
    """
    log = Path(f".overnight/logs/{n}.log")
    issue = sh("gh", "issue", "view", str(n))
    base = sh("git", "rev-parse", "HEAD")
    cost, plan = 0.0, ""
    if args.reviewer != "none":
        run = run_agent(args, args.reviewer, args.reviewer_model, PLAN.format(issue=issue), log, read_only=True)
        plan = run.text
        cost += run.cost
        tidy()
        if run.broke:
            drop_reviewer(args, n, run.error)
            plan = ""
    prompt = WORKER.format(n=n) + (f"\nA planner suggests:\n\n{plan}\n" if plan else "")
    run = run_agent(args, args.harness, args.model, prompt, log)
    message = run.text
    cost += run.cost
    if run.broke:
        tidy(base)
        return None, cost, True
    tidy()  # keep only what the worker committed
    ok, tail = check(args, base, branch, log)
    broke = False
    if ok and args.reviewer != "none":
        diff = sh("git", "diff", f"{base}..HEAD")[:60000]
        run = run_agent(args, args.reviewer, args.reviewer_model,
                        REVIEW.format(n=n, issue=issue, diff=diff), log, read_only=True)
        review = run.text
        cost += run.cost
        tidy()
        if run.broke:
            drop_reviewer(args, n, run.error)
            message += "\n\nUnreviewed: the reviewer ran out of money or hit its usage limit."
        elif verdict(review) is None:
            # A crashed or truncated review is no review: the work does not stay.
            ok, tail = False, "the review gave no verdict"
            message += "\n\nReview:\n" + review[-800:]
        elif verdict(review) == "changes":
            green = sh("git", "rev-parse", "HEAD")
            run = run_agent(args, args.harness, args.model, WORKER.format(n=n) + "\n" + FIX.format(findings=review), log)
            cost += run.cost
            broke = run.broke
            tidy()
            fixed, why = (False, "it ran out of money") if broke else check(args, green, branch, log)
            if fixed:
                message = run.text + "\n\nAfter review:\n" + review[-800:]
            else:
                tidy(green)  # keep the green work from before the fix
                message += f"\n\nThe review's findings are not addressed: the fix pass failed ({why[-300:]}).\n\n" \
                           + review[-800:]
    if ok:
        sh("gh", "issue", "edit", str(n), "--add-label", DONE, "--remove-label", WORKING)
        sh("gh", "issue", "comment", str(n), "--body", f"Done on `{branch}`.\n\n{message}")
        note(n, title, "done", message)
    else:
        tidy(base)
        sh("gh", "issue", "edit", str(n), "--add-label", PARKED, "--remove-label", WORKING)
        sh("gh", "issue", "comment", str(n), "--body",
           f"Parked by the overnight run.\n\n{message}\n\n```\n{tail}\n```")
        note(n, title, "parked", f"{message}\n\n```\n{tail}\n```")
    return ("done" if ok else "parked"), cost, broke


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--harness", choices=["claude", "pi"], required=True, help="runs the workers")
    p.add_argument("--model", help="the workers' model, passed to the harness as --model "
                                   "(pi default: the gateway's `cloud`)")
    p.add_argument("--reviewer", choices=["claude", "pi", "none"], default="claude",
                   help="plans each issue and reviews green work (default claude)")
    p.add_argument("--reviewer-model", help="as --model, for the reviewer")
    p.add_argument("--base", help="the branch to start from (default: the repo's default branch)")
    p.add_argument("--label", default="ready-for-agent", help="issues to work (default ready-for-agent)")
    p.add_argument("--hours", type=float, default=8, help="stop starting issues after this (default 8)")
    p.add_argument("--max-issues", type=int, default=20)
    p.add_argument("--max-fails", type=int, default=3, help="stop after this many parks in a row (default 3)")
    p.add_argument("--issue-minutes", type=float, default=90, help="time limit per agent run (default 90)")
    p.add_argument("--verify-minutes", type=float, default=15,
                   help="time limit per ./verify.sh run, past which it counts as a fail (default 15)")
    p.add_argument("--issue-usd", type=float, default=10, help="claude only: budget per agent run (default 10)")
    p.add_argument("--max-cost", type=float, default=60,
                   help="stop past this total (default 60); pi is priced from DeepSeek's table")
    p.add_argument("--budget", type=float,
                   help="pi only: dollars this run may spend on the gateway's `cloud` model")
    p.add_argument("--off-peak", action="store_true",
                   help="work only in DeepSeek's off-peak hours, waiting through peak; weekends are all off-peak")
    p.add_argument("--off-peak-margin", type=int, default=20,
                   help="minutes before peak to stop starting issues (default 20)")
    p.add_argument("--board", type=int, help="GitHub project number to keep in sync with board-sync.py")
    p.add_argument("--yolo", action="store_true",
                   help="claude workers: bypassPermissions instead of auto; only inside a container or VM")
    args = p.parse_args()
    args.spend, args.unreviewed_from = None, None

    if not os.access("verify.sh", os.X_OK):
        sys.exit("no executable ./verify.sh here: run this from the repo root, after setting one up")
    if sh("git", "status", "--porcelain"):
        sys.exit("the working tree is not clean: commit or stash first")
    if args.budget and (args.harness != "pi" or args.model not in (None, "cloud")):
        sys.exit("--budget counts the gateway's `cloud` model, so it needs --harness pi and no other --model")
    sh("gh", "auth", "status")
    start = args.base or sh("gh", "repo", "view", "--json", "defaultBranchRef", "--jq", ".defaultBranchRef.name")
    if (on := sh("git", "branch", "--show-current")) != start:
        sys.exit(f"on {on or 'a detached HEAD'}, not {start}: the run branches from {start}, "
                 "so check it out or pass --base")
    Path(".overnight/logs").mkdir(parents=True, exist_ok=True)
    Path(".overnight/STOP").unlink(missing_ok=True)  # it ended an earlier run
    exclude = Path(sh("git", "rev-parse", "--git-path", "info/exclude"))
    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.touch()
    missing = [x for x in (".overnight/", f"/{PI_OVERRIDE}") if x not in exclude.read_text().splitlines()]
    if missing:
        with exclude.open("a") as f:
            f.write("\n" + "\n".join(missing) + "\n")
    if args.harness == "pi":
        allow_pi_writes()
    ok, tail = verify(args, Path(".overnight/logs/baseline.log"))
    if not ok:
        sys.exit(f"./verify.sh fails before any work, so nothing can be judged:\n{tail}")
    smoke_test(args, args.harness, args.model)
    if args.reviewer != "none":
        smoke_test(args, args.reviewer, args.reviewer_model)
    for label, colour in ((DONE, "0e8a16"), (PARKED, "d93f0b"), (WORKING, "5319e7")):
        sh("gh", "label", "create", label, "--color", colour, "--force")
    for stale in json.loads(sh("gh", "issue", "list", "--label", WORKING, "--json", "number")):
        sh("gh", "issue", "edit", str(stale["number"]), "--remove-label", WORKING)

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
        waiting = False
        while not (why := stop_reason(args, tried, fails, cost, deadline)):
            if args.off_peak and peak_soon(datetime.now(timezone.utc), args.off_peak_margin):
                if not waiting:
                    print("Peak hours: waiting for the off-peak window.", flush=True)
                waiting = True
                time.sleep(300)
                continue
            waiting = False
            issue = next_issue(args.label, tried, set(done))
            if not issue:
                why = "queue empty"
                break
            n, title = issue["number"], issue["title"]
            tried.add(n)
            print(f"#{n} {title}", flush=True)
            sh("gh", "issue", "edit", str(n), "--add-label", WORKING)
            board(args)
            outcome, spent, broke = work_issue(args, n, title, branch)
            cost += spent
            if outcome is None:
                sh("gh", "issue", "edit", str(n), "--remove-label", WORKING)
            else:
                (done if outcome == "done" else parked)[n] = title
                fails = 0 if outcome == "done" else fails + 1
                print(f"  {outcome}, ${spent:.2f}", flush=True)
            if broke:
                why = "out of money"
                break
            board(args)
    finally:
        board(args)

    gateway = f" (the gateway counted ${args.spend.read():.2f})" if args.spend else ""
    print(f"\nStopped: {why}. Branch {branch}, ${cost:.2f} spent{gateway}.")
    for heading, items in (("Done", done), ("Parked", parked)):
        if items:
            print(f"{heading}:\n" + "\n".join(f"  #{k} {v}" for k, v in items.items()))
    if args.unreviewed_from:
        print(f"The reviewer stopped at #{args.unreviewed_from}: it and later issues went unreviewed.")
    if done:
        closes = " ".join(f"Closes #{k}." for k in done)
        print(f"\nTo review: git push -u origin {branch} && gh pr create --draft --body '{closes}'")


if __name__ == "__main__":
    main()
