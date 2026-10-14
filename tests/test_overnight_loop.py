"""overnight-loop.py against fake gh, pi and claude on PATH, in a throwaway repo.

The loop's bugs live in how it treats processes, git state and GitHub between
issues, which unit tests of its helpers cannot reach. Each test runs the real
script in a scratch repo whose ./verify.sh fails when a file named BROKEN
exists, with stand-ins that each do one thing a real worker has done.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from datetime import datetime, timezone
from unittest import mock
from pathlib import Path

from _loader import load

SCRIPT = Path(__file__).resolve().parent.parent / "bin" / "overnight-loop.py"
loop = load("overnight-loop.py")

AGENT = textwrap.dedent('''\
    import json, os, re, subprocess, sys, time

    def prompt_of(argv):
        if "--" in argv and argv.index("--") + 1 < len(argv):
            return argv[argv.index("--") + 1]
        if "-p" in argv and argv.index("-p") + 1 < len(argv) and not argv[argv.index("-p") + 1].startswith("-"):
            return argv[argv.index("-p") + 1]
        return sys.stdin.read()

    def log(line):
        with open(os.environ["FAKE_LOG"], "a") as f:
            f.write(line + "\\n")

    def git(*args):
        subprocess.run(["git", *args], check=True, capture_output=True)

    def detached_sleep():
        child = subprocess.Popen(["sleep", "300"], start_new_session=True)
        with open(os.environ["FAKE_PIDS"], "a") as f:
            f.write(f"{child.pid}\\n")

    def act(name, prompt):
        if prompt.startswith("Plan the implementation"):
            role = "plan"
        elif prompt.startswith("Review this change"):
            role = "review"
        elif "A reviewer asked for changes" in prompt:
            role = "fix"
        elif "issue #" in prompt:
            role = "work"
        else:
            role = "ping"
        log(f"{name} {role} " + json.dumps(sys.argv[1:]))
        if role == "ping":
            return os.environ.get("FAKE_PING", "ok")
        if role == "plan":
            return "Plan: touch src."
        if role == "review":
            return os.environ.get("FAKE_REVIEW", "Looks fine.\\nVERDICT: approve")
        n = re.search(r"issue #(\\d+)", prompt).group(1)
        mode = os.environ.get("FAKE_WORK_" + n, os.environ.get("FAKE_WORK", "good"))
        if role == "fix":
            mode = os.environ.get("FAKE_FIX", "good")
        if mode == "hang":
            with open(os.environ["FAKE_PIDS"], "a") as f:
                f.write(f"{os.getpid()}\\n")
            time.sleep(600)
        if mode == "nocommit":
            return "could not finish"
        if mode == "branch":
            git("checkout", "-q", "-b", "feat/x")
        if mode == "gate":
            with open("verify.sh", "w") as f:
                f.write("#!/bin/sh\\nexit 0\\n")
            git("add", "verify.sh")
        if mode in ("bad",):
            open("BROKEN", "w").write("1")
            git("add", "BROKEN")
        if mode in ("verifyhang", "verifyleak"):
            open(mode, "w").write("1")
            git("add", mode)
        if mode == "leftover":
            detached_sleep()
        with open(f"feature{n}.txt", "a") as f:
            f.write(role + "\\n")
        git("add", f"feature{n}.txt")
        subject = "Add stuff" if mode == "badsubject" else f"feat: issue {n} ({role}) (#{n})"
        git("commit", "-qm", subject)
        return f"did #{n} as {role}"
''')

FAKE_PI = textwrap.dedent('''\
    #!/usr/bin/env python3
    import json, os, sys, time
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from agent import act, prompt_of
    prompt = prompt_of(sys.argv[1:])
    if os.environ.get("FAKE_ISSUE_TEXT"):
        # A tool result quoting the issue, as when the worker runs gh issue view.
        print(json.dumps({"type": "tool_execution_end", "toolName": "bash",
                          "result": {"content": [{"type": "text", "text": os.environ["FAKE_ISSUE_TEXT"]}]}}))
    text = act("pi", prompt)
    for i in range(3):
        print(json.dumps({"type": "message_update", "delta": "x" * 50}))
    message = {"role": "assistant", "model": "cloud", "timestamp": time.time() * 1000,
               "usage": {"input": 100000, "output": 20000, "cacheRead": 500000},
               "content": [{"type": "text", "text": text}], "stopReason": "stop"}
    if os.environ.get("FAKE_PI_ERROR"):
        message |= {"stopReason": "error", "errorMessage": os.environ["FAKE_PI_ERROR"], "content": []}
    print(json.dumps({"type": "message_end", "message": message}))
    print(json.dumps({"type": "agent_settled"}))
''')

FAKE_CLAUDE = textwrap.dedent('''\
    #!/usr/bin/env python3
    import json, os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from agent import act, prompt_of
    text = act("claude", prompt_of(sys.argv[1:]))
    result = {"type": "result", "subtype": "success", "is_error": False, "result": text, "total_cost_usd": 0.25}
    if os.environ.get("FAKE_CLAUDE_ERROR"):
        result |= {"is_error": True, "result": os.environ["FAKE_CLAUDE_ERROR"], "total_cost_usd": 0}
    print(json.dumps(result), flush=True)
    if os.environ.get("FAKE_CLAUDE_STDERR"):
        print("SessionEnd hook: done", file=sys.stderr)
''')

FAKE_GH = textwrap.dedent('''\
    #!/usr/bin/env python3
    """Stateful fake gh; its state is the JSON file $FAKE_GH_STATE."""
    import json, os, sys
    path = os.environ["FAKE_GH_STATE"]
    st = json.load(open(path))
    a = sys.argv[1:]
    with open(path + ".log", "a") as f:
        f.write(" ".join(a)[:200] + "\\n")

    def save():
        json.dump(st, open(path, "w"), indent=1)

    def opt(name, many=False):
        vals = [a[i + 1] for i, x in enumerate(a) if x == name]
        return vals if many else (vals[0] if vals else None)

    fail = os.environ.get("FAKE_GH_FAIL", "")
    if fail and fail in " ".join(a) and st.get("_failed", 0) < int(os.environ.get("FAKE_GH_FAIL_TIMES", "99")):
        st["_failed"] = st.get("_failed", 0) + 1
        save()
        print("HTTP 502: Bad Gateway", file=sys.stderr)
        sys.exit(1)
    if a[:2] in (["auth", "status"], ["label", "create"]):
        sys.exit(0)
    if a[:2] == ["repo", "view"]:
        print("main" if "defaultBranchRef" in " ".join(a) else json.dumps({"nameWithOwner": "greg/game"}))
        sys.exit(0)
    if a[0] == "api":
        sys.exit(1)  # no issue dependencies
    if a[:2] == ["issue", "list"]:
        label, state = opt("--label"), opt("--state") or "open"
        out = [{"number": int(n), "title": i["title"], "labels": [{"name": l} for l in i["labels"]]}
               for n, i in st["issues"].items()
               if (state == "all" or i["state"].lower() == state) and (not label or label in i["labels"])]
        print(json.dumps(out))
        sys.exit(0)
    if a[:2] == ["issue", "view"]:
        i = st["issues"][a[2]]
        if "--comments" in a:
            print("\\n--\\n".join(i.get("comments", [])))
        else:
            print(f"title:\\t{i['title']}\\nnumber:\\t{a[2]}\\n--\\n{i['body']}")
        sys.exit(0)
    if a[:2] == ["issue", "edit"]:
        i = st["issues"][a[2]]
        for l in opt("--add-label", True):
            if l not in i["labels"]:
                i["labels"].append(l)
        for l in opt("--remove-label", True):
            if l in i["labels"]:
                i["labels"].remove(l)
        save()
        sys.exit(0)
    if a[:2] == ["issue", "comment"]:
        st["issues"][a[2]].setdefault("comments", []).append(opt("--body"))
        save()
        sys.exit(0)
    print("fake gh: unhandled " + " ".join(a), file=sys.stderr)
    sys.exit(1)
''')

VERIFY = textwrap.dedent('''\
    #!/bin/sh
    if [ -e verifyhang ]; then sleep 600; fi
    if [ -e verifyleak ]; then sh -c 'echo $$ >> "$FAKE_PIDS"; exec sleep 300' & fi
    test ! -e BROKEN
''')


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


class LoopTest(unittest.TestCase):
    """A scratch repo on main, two ready issues, and the fakes first on PATH."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.bin, self.repo = root / "bin", root / "repo"
        self.bin.mkdir()
        self.repo.mkdir()
        (self.bin / "agent.py").write_text(AGENT)
        for name, body in (("pi", FAKE_PI), ("claude", FAKE_CLAUDE), ("gh", FAKE_GH)):
            (self.bin / name).write_text(body)
            (self.bin / name).chmod(0o755)
        self.state = root / "gh.json"
        self.issues({1: "First", 2: "Second"})
        self.agent_log, self.pids = root / "agents.log", root / "pids"
        self.agent_log.touch()
        self.pids.touch()
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(("DEEPSEEK", "LITELLM", "FAKE_"))}
        self.env |= {"PATH": f"{self.bin}:{os.environ['PATH']}", "HOME": str(root),
                     "FAKE_GH_STATE": str(self.state), "FAKE_LOG": str(self.agent_log),
                     "FAKE_PIDS": str(self.pids), "LITELLM_URL": "http://127.0.0.1:9"}
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "t")
        self.git("config", "user.email", "t@t")
        (self.repo / "verify.sh").write_text(VERIFY)
        (self.repo / "verify.sh").chmod(0o755)
        (self.repo / "CLAUDE.md").write_text("# rules\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "init")

    def tearDown(self) -> None:
        for pid in map(int, self.pids.read_text().split()):
            if alive(pid):
                os.kill(pid, signal.SIGKILL)
        self.tmp.cleanup()

    def issues(self, titles: dict[int, str], body: str = "Done when: it works.") -> None:
        self.state.write_text(json.dumps({"issues": {
            str(n): {"title": t, "state": "OPEN", "labels": ["ready-for-agent"], "body": body}
            for n, t in titles.items()}}))

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.repo, capture_output=True, text=True, check=True).stdout

    def labels(self, n: int) -> list[str]:
        return json.loads(self.state.read_text())["issues"][str(n)]["labels"]

    def comments(self, n: int) -> list[str]:
        return json.loads(self.state.read_text())["issues"][str(n)].get("comments", [])

    def run_loop(self, *args: str, timeout: float = 60, **env: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=self.repo, env=self.env | env,
                              capture_output=True, text=True, timeout=timeout)

    def roles(self) -> list[str]:
        return [" ".join(line.split()[:2]) for line in self.agent_log.read_text().splitlines()]


class TestHappyPath(LoopTest):
    def test_two_issues_done_and_labelled(self):
        out = self.run_loop("--harness", "pi", "--reviewer", "none")
        self.assertIn("Stopped: queue empty", out.stdout, out.stderr)
        self.assertIn("overnight:done", self.labels(1))
        self.assertIn("overnight:done", self.labels(2))
        self.assertIn("feat: issue 2 (work) (#2)", self.git("log", "--format=%s"))


    def test_a_stop_file_left_by_an_earlier_run_is_ignored(self):
        (self.repo / ".overnight").mkdir()
        (self.repo / ".overnight" / "STOP").touch()
        (self.repo / ".git" / "info" / "exclude").write_text(".overnight/\n")
        out = self.run_loop("--harness", "pi", "--reviewer", "none")
        self.assertIn("overnight:done", self.labels(1), out.stdout + out.stderr)


class TestOutOfMoney(LoopTest):
    def test_an_issue_that_mentions_insufficient_balance_is_worked(self):
        out = self.run_loop("--harness", "pi", "--reviewer", "none",
                            FAKE_ISSUE_TEXT='Show "Insufficient Balance" when the player cannot afford it.')
        self.assertNotIn("out of money", out.stdout)
        self.assertIn("overnight:done", self.labels(1))

    def test_a_pi_turn_that_fails_on_balance_stops_the_run(self):
        out = self.run_loop("--harness", "pi", "--reviewer", "none",
                            FAKE_PI_ERROR="402 Insufficient Balance")
        self.assertIn("Stopped: out of money", out.stdout, out.stderr)
        self.assertNotIn("overnight:parked", self.labels(1))
        self.assertNotIn("overnight:working", self.labels(1))

    def test_a_claude_usage_limit_stops_the_run(self):
        out = self.run_loop("--harness", "claude", "--reviewer", "none",
                            FAKE_CLAUDE_ERROR="Claude AI usage limit reached")
        self.assertIn("Stopped: out of money", out.stdout, out.stderr)


class TestVerify(LoopTest):
    def test_a_hung_verify_times_out_and_parks(self):
        started = time.monotonic()
        out = self.run_loop("--harness", "pi", "--reviewer", "none", "--verify-minutes", "0.05",
                            FAKE_WORK_1="verifyhang")
        self.assertLess(time.monotonic() - started, 40)
        self.assertIn("overnight:parked", self.labels(1), out.stdout + out.stderr)
        self.assertIn("timed out", self.comments(1)[-1])
        self.assertIn("overnight:done", self.labels(2))


class TestGate(LoopTest):
    def test_a_worker_that_edits_verify_sh_is_parked(self):
        out = self.run_loop("--harness", "pi", "--reviewer", "none", FAKE_WORK_1="gate")
        self.assertIn("overnight:parked", self.labels(1), out.stdout + out.stderr)
        self.assertIn("verify.sh", self.comments(1)[-1])
        self.assertNotIn("exit 0", (self.repo / "verify.sh").read_text())


def utc(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=timezone.utc)


class TestOffPeak(unittest.TestCase):
    # 2026-10-13 is a Tuesday: peak 01:00-04:00 and 06:00-10:00 UTC.
    def test_waits_when_peak_opens_inside_the_margin(self):
        self.assertTrue(loop.peak_soon(utc(13, 0, 45), 20), "20:45 EDT, a normal start time")
        self.assertTrue(loop.peak_soon(utc(13, 2), 20))
        self.assertFalse(loop.peak_soon(utc(13, 4), 20))
        self.assertFalse(loop.peak_soon(utc(17, 2), 20), "Saturday")

    def test_peak_pauses_the_run_rather_than_ending_it(self):
        args = argparse.Namespace(off_peak=True, off_peak_margin=20, max_issues=20, max_fails=3,
                                  spend=None, max_cost=60)
        with mock.patch.object(loop.preflight, "minutes_until_peak", return_value=5):
            self.assertIsNone(loop.stop_reason(args, set(), 0, 0.0, time.time() + 3600))


class TestPiEvents(unittest.TestCase):
    def test_reads_errors_only_from_error_events(self):
        quoted = json.dumps({"type": "tool_execution_end", "result": "Insufficient Balance"})
        failed = json.dumps({"type": "message_end", "message": {
            "role": "assistant", "stopReason": "error", "errorMessage": "402 Insufficient Balance"}})
        retry = json.dumps({"type": "auto_retry_end", "finalError": "budget_exceeded"})
        self.assertFalse(loop.pi_result(quoted).broke)
        self.assertTrue(loop.pi_result(failed).broke)
        self.assertTrue(loop.pi_result(retry).broke)


if __name__ == "__main__":
    unittest.main()
