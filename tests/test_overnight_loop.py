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
import re
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
import urllib.error
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
        with open(os.environ["FAKE_LOG"] + ".prompts", "a") as f:
            f.write(prompt + "\\n")
        return role, work(role, prompt)

    def failing(name, role):
        """The error to end on, if FAKE_ERROR_ROLES names this role, or name:role."""
        roles = os.environ.get("FAKE_ERROR_ROLES", "work,fix").split(",")
        if role in roles or f"{name}:{role}" in roles:
            return os.environ.get("FAKE_ERROR")
        return None

    def work(role, prompt):
        if role == "ping":
            return os.environ.get("FAKE_PING", "ok")
        if role == "plan":
            return "Plan: touch src."
        if role == "review":
            if os.environ.get("FAKE_REVIEW_MOVE") == "detach":
                git("checkout", "-q", "--detach", "main")
            elif os.environ.get("FAKE_REVIEW_MOVE") == "gone":
                git("checkout", "-q", "--detach", "main")
                git("branch", "-D", "-q", subprocess.run(["git", "branch", "--list", "overnight/*", "--format=%(refname:short)"], capture_output=True, text=True).stdout.split()[0])
            elif os.environ.get("FAKE_REVIEW_MOVE"):
                git("checkout", "-q", os.environ["FAKE_REVIEW_MOVE"])
            return os.environ.get("FAKE_REVIEW", "Looks fine.\\nVERDICT: approve")
        n = re.search(r"issue #(\\d+)", prompt).group(1)
        mode = os.environ.get("FAKE_WORK_" + n, os.environ.get("FAKE_WORK", "good"))
        if role == "fix":
            mode = os.environ.get("FAKE_FIX", "good")
        if mode in ("leftover", "leftoverhang"):
            detached_sleep()
        if mode == "ide":
            # Stands in for a language server: its editor parent outlives the worker.
            subprocess.Popen([sys.executable, "-c", "import os, subprocess, sys, time; "
                              "p = subprocess.Popen(['sleep', '300']); "
                              "open(sys.argv[1], 'w').write(str(p.pid)); time.sleep(300)",
                              os.environ["FAKE_PIDS"] + ".spare"], start_new_session=True)
            time.sleep(0.5)
        if mode in ("hang", "leftoverhang"):
            with open(os.environ["FAKE_PIDS"], "a") as f:
                f.write(f"{os.getpid()}\\n")
            time.sleep(600)
        retry = "blocked by a permission classifier" in prompt
        if mode == "blocked" and not retry:
            open(f"first{n}.txt", "w").write("committed\\n")
            git("add", f"first{n}.txt")
            git("commit", "-qm", f"feat: first (#{n})")
            open(f"second{n}.txt", "w").write("left uncommitted\\n")
            return os.environ["FAKE_BLOCKED"]
        if mode == "blocked":
            git("add", "-A")
            if os.environ.get("FAKE_RETRY_BREAKS"):
                open("BROKEN", "w").write("1")
                git("add", "BROKEN")
        if mode == "nocommit":
            return "could not finish"
        if mode == "branch":
            git("checkout", "-q", "-b", "feat/x")
        if mode == "gate":
            with open("verify.sh", "w") as f:
                f.write("#!/bin/sh\\nexit 0\\n")
            git("add", "verify.sh")
        if mode == "gate2":
            with open("verify.sh", "w") as f:
                f.write("#!/bin/sh\\nexit 0 # again\\n")
            git("add", "verify.sh")
        if mode in ("bad",):
            open("BROKEN", "w").write("1")
            git("add", "BROKEN")
        if mode in ("verifyhang", "verifyleak"):
            open(mode, "w").write("1")
            git("add", mode)
        if mode == "terminal":
            # Stands in for a shell Greg opens in the repo mid-run.
            import pty
            pid, _ = pty.fork()
            if pid == 0:
                import signal
                signal.signal(signal.SIGHUP, signal.SIG_IGN)
                os.execvp("sleep", ["sleep", "300"])
            with open(os.environ["FAKE_PIDS"] + ".spare", "a") as f:
                f.write(f"{pid}\\n")
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
    from agent import act, failing, prompt_of
    prompt = prompt_of(sys.argv[1:])
    if os.environ.get("FAKE_ISSUE_TEXT"):
        # A tool result quoting the issue, as when the worker runs gh issue view.
        print(json.dumps({"type": "tool_execution_end", "toolName": "bash",
                          "result": {"content": [{"type": "text", "text": os.environ["FAKE_ISSUE_TEXT"]}]}}))
    NAME = "pi"
    with open(os.environ["FAKE_LOG"] + ".tmpdir", "a") as f:
        f.write(os.environ.get("TMPDIR", "") + "\\n")
    with open(os.environ["FAKE_LOG"] + ".depth", "a") as f:
        f.write(prompt[:6] + "=" + os.environ.get("PI_SUBAGENT_DEPTH", "") + "\\n")
    config = ".pi/extensions/pi-permission-system/config.json"
    with open(os.environ["FAKE_LOG"] + ".pi-config", "a") as f:
        f.write((open(config).read() if os.path.exists(config) else "missing\\n"))
    role, text = act(NAME, prompt)
    for i in range(3):
        print(json.dumps({"type": "message_update", "delta": "x" * 50}))
    message = {"role": "assistant", "model": "cloud", "timestamp": time.time() * 1000,
               "usage": {"input": 100000, "output": 20000, "cacheRead": 500000},
               "content": [{"type": "text", "text": text}], "stopReason": "stop"}
    if failing(NAME, role):
        message |= {"stopReason": "error", "errorMessage": failing(NAME, role), "content": []}
    print(json.dumps({"type": "message_end", "message": message}))
    print(json.dumps({"type": "agent_settled"}))
''')

FAKE_CLAUDE = textwrap.dedent('''\
    #!/usr/bin/env python3
    import json, os, signal, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from agent import act, failing, prompt_of

    def interrupted(*_):
        # Claude ends the turn on SIGINT and still prints its result.
        print(json.dumps({"type": "result", "is_error": False, "result": "interrupted", "total_cost_usd": 0.25}))
        sys.exit(130)

    signal.signal(signal.SIGINT, interrupted)
    NAME = "claude"
    with open(os.environ["FAKE_LOG"] + ".env", "a") as f:
        f.write(os.environ.get("CLAUDE_CODE_DISABLE_BACKGROUND_TASKS", "") + "\\n")
    if "ok" in sys.argv[1:]:  # the usage-limit probe
        print("ok")
        sys.exit(0)
    role, text = act(NAME, prompt_of(sys.argv[1:]))
    limit = os.environ.get("FAKE_LIMIT_ONCE")
    result = {"type": "result", "subtype": "success", "is_error": False, "result": text, "total_cost_usd": 0.25}
    if failing(NAME, role):
        result |= {"is_error": True, "result": failing(NAME, role), "total_cost_usd": 0}
    elif limit and os.path.exists(limit):
        os.remove(limit)
        result |= {"is_error": True, "result": "Usage limit reached · limit resets 3:45pm", "total_cost_usd": 0}
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
    if [ -e verifyleak ]; then python3 -c "import os, subprocess; p = subprocess.Popen(['sleep', '300'], start_new_session=True); open(os.environ['FAKE_PIDS'], 'a').write(f'{p.pid}\\n')"; fi
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

    def run_loop(self, *args: str, timeout: float = 60, no_sleep: bool = False,
                 **env: str) -> subprocess.CompletedProcess:
        cmd = [sys.executable, str(SCRIPT), *args]
        if no_sleep:  # gh retries back off for most of a minute
            cmd = [sys.executable, "-c", "import runpy, sys, time; time.sleep = lambda s: None; "
                   f"sys.argv = sys.argv[1:]; runpy.run_path(sys.argv[0], run_name='__main__')", *cmd[1:]]
        return subprocess.run(cmd, cwd=self.repo, env=self.env | env, capture_output=True, text=True,
                              timeout=timeout)

    def roles(self) -> list[str]:
        return [" ".join(line.split()[:2]) for line in self.agent_log.read_text().splitlines()]


class TestHappyPath(LoopTest):
    def test_two_issues_done_and_labelled(self):
        out = self.run_loop("--harness", "pi", "--reviewer", "none")
        self.assertIn("Stopped: queue empty", out.stdout, out.stderr)
        self.assertIn("overnight:done", self.labels(1))
        self.assertIn("overnight:done", self.labels(2))
        self.assertIn("feat: issue 2 (work) (#2)", self.git("log", "--format=%s"))
        self.assertRegex(out.stdout, r"gh pr create --draft --title 'Overnight run [\d-]+' --body 'Closes #1. Closes #2.'")


    def test_a_stop_file_left_by_an_earlier_run_is_ignored(self):
        (self.repo / ".overnight").mkdir()
        (self.repo / ".overnight" / "STOP").touch()
        (self.repo / ".git" / "info" / "exclude").write_text(".overnight/\n")
        out = self.run_loop("--harness", "pi", "--reviewer", "none")
        self.assertIn("overnight:done", self.labels(1), out.stdout + out.stderr)


    def test_a_failing_commit_hook_does_not_block_the_progress_note(self):
        hook = self.repo / ".git" / "hooks" / "commit-msg"
        hook.write_text('#!/bin/sh\n! grep -q "chore(overnight)" "$1"\n')
        hook.chmod(0o755)
        out = self.run_loop("--harness", "pi", "--reviewer", "none")
        self.assertIn("Stopped: queue empty", out.stdout, out.stderr)
        self.assertIn("progress for #2", self.git("log", "--format=%s"))


class TestModel(LoopTest):
    def test_pi_defaults_to_the_gateway_cloud_model(self):
        self.run_loop("--harness", "pi", "--reviewer", "none")
        work = [json.loads(line.split(" ", 2)[2]) for line in self.agent_log.read_text().splitlines()
                if line.startswith("pi work")]
        self.assertIn(["--model", "cloud"], [w[i:i + 2] for w in work for i in range(len(w))])
        self.assertTrue(all("litellm" in w for w in work))

    def test_a_budget_takes_the_cloud_model_by_its_full_name(self):
        out = self.run_loop("--harness", "pi", "--reviewer", "none", "--model", "litellm/cloud", "--budget", "1")
        self.assertNotIn("--budget counts", out.stderr)
        self.assertIn('"--model", "cloud"', self.agent_log.read_text())

    def test_a_named_model_goes_through_unchanged(self):
        self.run_loop("--harness", "pi", "--reviewer", "none", "--model", "deepseek/deepseek-flash")
        work = self.agent_log.read_text()
        self.assertIn('"--model", "deepseek/deepseek-flash"', work)
        self.assertNotIn("litellm", work)

    def test_a_model_that_cannot_answer_stops_before_any_issue(self):
        out = self.run_loop("--harness", "pi", "--reviewer", "none",
                            FAKE_ERROR="No API key found for deepseek.", FAKE_ERROR_ROLES="ping")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("No API key found for deepseek", out.stderr)
        self.assertEqual(self.roles(), ["pi ping"])
        self.assertEqual(self.labels(1), ["ready-for-agent"])

    def test_the_reviewer_is_tried_too(self):
        out = self.run_loop("--harness", "pi", FAKE_ERROR="Not logged in", FAKE_ERROR_ROLES="claude:ping")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("Not logged in", out.stderr)
        self.assertEqual(self.roles(), ["pi ping", "claude ping"])


    def test_claude_runs_answer_no_permission_prompts(self):
        self.run_loop("--harness", "claude", "--reviewer", "none")
        self.assertIn('"--permission-prompts", "none"', self.agent_log.read_text())


class TestPiWrites(LoopTest):
    override = Path(".pi/extensions/pi-permission-system/config.json")

    def test_pi_workers_may_write_and_git_never_sees_it(self):
        out = self.run_loop("--harness", "pi", "--reviewer", "none")
        seen = Path(str(self.agent_log) + ".pi-config").read_text().splitlines()
        self.assertEqual(json.loads(seen[-1])["permission"]["write"], {"*": "allow"}, out.stderr)
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_the_override_goes_when_the_run_ends(self):
        self.run_loop("--harness", "pi", "--reviewer", "none")
        self.assertFalse((self.repo / ".pi").exists(), "interactive pi here would write without asking")

    def test_a_repo_that_commits_its_own_config_keeps_it(self):
        (self.repo / self.override).parent.mkdir(parents=True)
        (self.repo / self.override).write_text('{"permission": {"write": {"*": "deny"}}}')
        self.git("add", "-A")
        self.git("commit", "-qm", "pi config")
        out = self.run_loop("--harness", "pi", "--reviewer", "none")
        self.assertIn("deny", (self.repo / self.override).read_text())
        self.assertIn("repo's own", out.stdout)


class TestOutOfMoney(LoopTest):
    def test_an_issue_that_mentions_insufficient_balance_is_worked(self):
        out = self.run_loop("--harness", "pi", "--reviewer", "none",
                            FAKE_ISSUE_TEXT='Show "Insufficient Balance" when the player cannot afford it.')
        self.assertNotIn("out of money", out.stdout)
        self.assertIn("overnight:done", self.labels(1))

    def test_a_pi_turn_that_fails_on_balance_stops_the_run(self):
        out = self.run_loop("--harness", "pi", "--reviewer", "none",
                            FAKE_ERROR="402 Insufficient Balance")
        self.assertIn("Stopped: out of money", out.stdout, out.stderr)
        self.assertNotIn("overnight:parked", self.labels(1))
        self.assertNotIn("overnight:working", self.labels(1))

    def test_a_claude_usage_limit_is_waited_out(self):
        once = Path(self.tmp.name) / "limit-once"
        once.touch()
        out = self.run_loop("--harness", "claude", "--reviewer", "none", no_sleep=True, FAKE_LIMIT_ONCE=str(once))
        self.assertIn("claude usage limit hit; probing again", out.stdout, out.stderr)
        self.assertNotIn("out of money", out.stdout)
        self.assertIn("overnight:done", self.labels(1))


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


class TestEfficiency(LoopTest):
    def prompts(self) -> str:
        return Path(str(self.agent_log) + ".prompts").read_text()

    def argv(self, role: str) -> list[list[str]]:
        return [json.loads(line.split(" ", 2)[2]) for line in self.agent_log.read_text().splitlines()
                if line.split()[1] == role]

    def label(self, n: int, name: str) -> None:
        st = json.loads(self.state.read_text())
        st["issues"][str(n)]["labels"].append(name)
        self.state.write_text(json.dumps(st))

    def test_the_worker_gets_the_issue_inline_and_the_reading_rules(self):
        self.issues({1: "First"}, body="Done when: the zebra is striped.")
        self.run_loop("--harness", "pi", "--reviewer", "none")
        text = self.prompts()
        self.assertIn("Done when: the zebra is striped.", text)
        self.assertNotIn("Read the issue with", text)
        self.assertIn("never\n   cat a whole large file", text)
        self.assertIn("one-suite test script", text)

    def test_the_reviewer_is_capped_and_kept_out_of_the_loops_files(self):
        out = self.run_loop("--harness", "pi", "--reviewer", "pi")
        review = "Review this change" + self.prompts().split("Review this change")[1].split("The diff")[0]
        self.assertIn("Never read .overnight/", review)
        self.assertIn("under 25 tool calls", review)
        argv = self.argv("review")[0]
        self.assertEqual(argv[argv.index("--tools") + 1], "read,grep,find,ls,bash", out.stderr)
        self.assertEqual(argv[argv.index("--thinking") + 1], "high")
        self.assertEqual(self.argv("work")[0].count("--thinking"), 0)

    def test_the_cap_grows_with_the_diff(self):
        self.assertEqual(min(60, 25 + 2000 // 10), 60)
        self.assertIn("under {calls} tool calls", loop.REVIEW)

    def test_a_claude_reviewer_gets_no_bash_and_no_thinking_flag(self):
        self.run_loop("--harness", "pi", "--reviewer", "claude")
        self.assertNotIn("--thinking", self.argv("review")[0])
        self.assertIn("You can read, grep", self.prompts())

    def test_reviewer_thinking_is_passed_on(self):
        self.run_loop("--harness", "pi", "--reviewer", "pi", "--reviewer-thinking", "medium")
        argv = self.argv("review")[0]
        self.assertEqual(argv[argv.index("--thinking") + 1], "medium")

    def test_scratch_files_live_under_the_git_dir(self):
        self.run_loop("--harness", "pi", "--reviewer", "none")
        scratch = self.repo / ".git" / "overnight-tmp"
        self.assertTrue((scratch / "agent.out").exists())
        self.assertTrue((scratch / "prompt.md").exists())
        self.assertFalse((self.repo / ".overnight" / "agent.out").exists())
        self.assertTrue((self.repo / ".overnight" / "logs" / "1.log").exists())

    def test_workers_get_a_repo_local_tmpdir(self):
        self.run_loop("--harness", "pi", "--reviewer", "none")
        want = str((self.repo / ".git" / "overnight-tmp" / "tmp").resolve())
        seen = Path(str(self.agent_log) + ".tmpdir").read_text().split()
        self.assertEqual(set(seen), {want})

    def test_pi_runs_without_skills(self):
        self.run_loop("--harness", "pi", "--reviewer", "pi")
        for role in ("work", "plan", "review", "ping"):
            self.assertIn("--no-skills", self.argv(role)[0], role)

    def test_the_fix_pass_resumes_the_workers_pi_session(self):
        self.issues({1: "First"})
        out = self.run_loop("--harness", "pi", "--reviewer", "pi", FAKE_REVIEW="Fix it.\nVERDICT: changes")
        work, fix = self.argv("work")[0], self.argv("fix")[0]
        self.assertIn("--session-id", work, out.stderr)
        self.assertEqual(fix[fix.index("--session-id") + 1], work[work.index("--session-id") + 1])
        self.assertNotIn("--no-session", fix)
        self.assertIn("--no-session", self.argv("review")[0])
        self.assertEqual(self.prompts().count("You are one worker"), 2)

    def test_a_reviewer_that_checks_out_main_leaves_main_alone(self):
        self.issues({1: "First"})
        main = self.git("rev-parse", "main").strip()
        out = self.run_loop("--harness", "pi", "--reviewer", "pi", FAKE_REVIEW_MOVE="main")
        self.assertEqual(self.git("rev-parse", "main").strip(), main, out.stdout + out.stderr)
        self.assertIn("overnight:done", self.labels(1))

    def test_a_fix_after_a_detached_review_is_kept(self):
        self.issues({1: "First"})
        out = self.run_loop("--harness", "pi", "--reviewer", "pi", FAKE_REVIEW_MOVE="detach",
                            FAKE_REVIEW="Fix it.\nVERDICT: changes")
        self.assertIn("overnight:done", self.labels(1), out.stdout + out.stderr)
        branch = self.git("branch", "--show-current").strip()
        self.assertIn("(fix)", self.git("log", "--format=%s", branch))

    def test_a_later_unlabelled_issue_cannot_edit_a_gate_a_labelled_one_changed(self):
        self.label(1, "gate-change")
        out = self.run_loop("--harness", "pi", "--reviewer", "none", FAKE_WORK_1="gate", FAKE_WORK_2="gate2")
        self.assertIn("overnight:done", self.labels(1), out.stdout + out.stderr)
        self.assertIn("overnight:parked", self.labels(2), out.stdout + out.stderr)

    def test_a_later_unlabelled_issue_may_leave_the_gate_alone(self):
        self.label(1, "gate-change")
        self.run_loop("--harness", "pi", "--reviewer", "none", FAKE_WORK_1="gate")
        self.assertIn("overnight:done", self.labels(2))

    def test_only_the_reviewer_keeps_pis_bash_guard(self):
        self.run_loop("--harness", "pi", "--reviewer", "pi")
        self.assertNotIn("--bash-guard-disabled", self.argv("review")[0])
        self.assertIn("--bash-guard-disabled", self.argv("work")[0])

    def test_the_pi_reviewer_runs_at_subagent_depth_and_workers_do_not(self):
        self.run_loop("--harness", "pi", "--reviewer", "pi")
        seen = Path(str(self.agent_log) + ".depth").read_text().splitlines()
        self.assertIn("Review=1", seen)
        self.assertIn("You ar=", seen)

    def test_a_reviewer_that_deletes_the_lane_branch_parks_the_issue(self):
        self.issues({1: "First"})
        out = self.run_loop("--harness", "pi", "--reviewer", "pi", FAKE_REVIEW_MOVE="gone")
        self.assertIn("overnight:parked", self.labels(1), out.stdout + out.stderr)
        self.assertIn("could not get back", self.comments(1)[-1])
        self.assertNotIn("progress for #1", self.git("log", "--format=%s", "main"))

    def test_the_reviewer_is_told_to_gate_through_gateslot(self):
        self.assertIn("gateslot.py -- ./verify.sh", loop.REVIEW_BASH)

    def test_a_claude_fix_pass_still_gets_the_full_prompt(self):
        self.issues({1: "First"})
        self.run_loop("--harness", "claude", "--reviewer", "claude", FAKE_REVIEW="Fix it.\nVERDICT: changes")
        self.assertEqual(self.prompts().count("You are one worker"), 2)

    def test_a_size_s_issue_skips_the_plan_stage(self):
        self.label(1, "size:S")
        self.run_loop("--harness", "pi", "--reviewer", "pi")
        plans = [line for line in self.roles() if line.endswith(" plan")]
        self.assertEqual(len(plans), 1, self.roles())  # issue 2 only
        self.assertIn("No planner ran", self.prompts())

    def test_a_gate_label_lets_an_issue_change_the_gate(self):
        self.issues({1: "First"})
        self.label(1, "gate-change")
        out = self.run_loop("--harness", "pi", "--reviewer", "pi", FAKE_WORK_1="gate")
        self.assertIn("overnight:done", self.labels(1), out.stdout + out.stderr)
        self.assertIn("scrutinise those changes", self.prompts())

    def test_the_gate_label_is_configurable(self):
        self.issues({1: "First"})
        self.label(1, "custom")
        self.run_loop("--harness", "pi", "--reviewer", "none", "--gate-label", "custom", FAKE_WORK_1="gate")
        self.assertIn("overnight:done", self.labels(1))

    def test_without_the_label_the_gate_still_parks(self):
        self.issues({1: "First"})
        self.run_loop("--harness", "pi", "--reviewer", "pi", FAKE_WORK_1="gate")
        self.assertIn("overnight:parked", self.labels(1))
        self.assertNotIn("scrutinise those changes", self.prompts())


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


class TestClaudeCost(LoopTest):
    def test_counts_cost_when_stderr_follows_the_result(self):
        out = self.run_loop("--harness", "claude", "--reviewer", "none", FAKE_CLAUDE_STDERR="1")
        self.assertIn("$0.50 at list price", out.stdout, out.stderr)

    def test_counts_the_cost_of_a_run_that_timed_out(self):
        out = self.run_loop("--harness", "claude", "--reviewer", "none", "--issue-minutes", "0.05",
                            FAKE_WORK_1="hang")
        self.assertIn("$0.50 at list price", out.stdout, out.stderr)
        self.assertIn("overnight:parked", self.labels(1))


class TestVerdict(LoopTest):
    def test_reads_the_last_verdict_through_emphasis(self):
        self.assertEqual(loop.verdict("Fine.\n**VERDICT: changes**"), "changes")
        self.assertEqual(loop.verdict("VERDICT: changes.\n\n1. add a test"), "changes")
        self.assertEqual(loop.verdict("**Verdict:** approve"), "approve")
        self.assertEqual(loop.verdict("VERDICT: changes\nOn reflection, VERDICT: approve"), "approve")
        self.assertIsNone(loop.verdict("Reached maximum turns"))

    def test_reads_approved_and_change_as_verdicts(self):
        self.assertEqual(loop.verdict("VERDICT: Approved"), "approve")
        self.assertEqual(loop.verdict("VERDICT: change requested"), "changes")

    def test_a_verdict_in_bold_gets_its_fix_pass(self):
        self.run_loop("--harness", "pi", "--reviewer", "claude", FAKE_REVIEW="1. add a test\n**VERDICT: changes**")
        self.assertIn("pi fix", self.roles())

    def test_a_review_without_a_verdict_parks_the_issue(self):
        out = self.run_loop("--harness", "pi", "--reviewer", "claude", FAKE_REVIEW="I ran out of turns.")
        self.assertIn("overnight:parked", self.labels(1), out.stdout + out.stderr)
        self.assertIn("no verdict", self.comments(1)[-1])
        self.assertNotIn("feat: issue 1", self.git("log", "--format=%s"))


class TestFixPass(LoopTest):
    def test_a_fix_that_breaks_verify_keeps_the_green_work(self):
        out = self.run_loop("--harness", "pi", "--reviewer", "claude", FAKE_FIX="bad",
                            FAKE_REVIEW="Add a test.\nVERDICT: changes")
        self.assertIn("overnight:done", self.labels(1), out.stdout + out.stderr)
        self.assertIn("not addressed", self.comments(1)[-1])
        log = self.git("log", "--format=%s")
        self.assertIn("feat: issue 1 (work) (#1)", log)
        self.assertNotIn("(fix)", log)
        self.assertFalse((self.repo / "BROKEN").exists())

    def test_a_fix_that_runs_out_of_money_keeps_the_work_and_stops(self):
        out = self.run_loop("--harness", "pi", "--reviewer", "claude", FAKE_ERROR="402 Insufficient Balance",
                            FAKE_ERROR_ROLES="pi:fix", FAKE_REVIEW="VERDICT: changes")
        self.assertIn("Stopped: out of money", out.stdout, out.stderr)
        self.assertIn("overnight:done", self.labels(1))
        self.assertIn("feat: issue 1 (work) (#1)", self.git("log", "--format=%s"))
        self.assertEqual(self.labels(2), ["ready-for-agent"])


class TestReviewerLimit(LoopTest):
    def test_a_reviewer_out_of_money_leaves_the_rest_unreviewed(self):
        out = self.run_loop("--harness", "pi", "--reviewer", "claude",
                            FAKE_ERROR="Credit balance is too low", FAKE_ERROR_ROLES="claude:review")
        self.assertIn("Stopped: queue empty", out.stdout, out.stderr)
        self.assertIn("overnight:done", self.labels(1))
        self.assertIn("overnight:done", self.labels(2))
        self.assertIn("Unreviewed", self.comments(1)[-1])
        self.assertIn("feat: issue 1 (work) (#1)", self.git("log", "--format=%s"))
        self.assertNotIn("claude plan", self.roles()[3:], "no reviewer after it stopped")
        self.assertIn("went unreviewed", out.stdout)

    def test_a_planner_out_of_money_does_not_end_the_run(self):
        out = self.run_loop("--harness", "pi", "--reviewer", "claude",
                            FAKE_ERROR="Credit balance is too low", FAKE_ERROR_ROLES="claude:plan")
        self.assertIn("Stopped: queue empty", out.stdout, out.stderr)
        self.assertIn("overnight:done", self.labels(1))


class TestBranch(LoopTest):
    def test_refuses_to_start_off_the_default_branch(self):
        self.git("checkout", "-q", "-b", "overnight/last-night")
        out = self.run_loop("--harness", "pi", "--reviewer", "none")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("not main", out.stderr)
        self.assertEqual(self.agent_log.read_text(), "")

    def test_base_names_another_start(self):
        self.git("checkout", "-q", "-b", "dev")
        out = self.run_loop("--harness", "pi", "--reviewer", "none", "--base", "dev")
        self.assertIn("overnight:done", self.labels(1), out.stderr)

    def test_a_worker_that_switches_branch_is_parked(self):
        out = self.run_loop("--harness", "pi", "--reviewer", "none", FAKE_WORK_1="branch")
        self.assertIn("overnight:parked", self.labels(1), out.stdout + out.stderr)
        self.assertIn("feat/x", self.comments(1)[-1])
        self.assertTrue(self.git("branch", "--show-current").startswith("overnight/"))
        self.assertIn("overnight:done", self.labels(2))
        self.assertIn("feat: issue 2", self.git("log", "--format=%s"))


class TestCaps(unittest.TestCase):
    def test_a_budget_does_not_lift_the_cost_cap(self):
        args = argparse.Namespace(off_peak=False, max_issues=20, max_fails=3, max_cost=5, budget=3,
                                  spend=mock.Mock(read=mock.Mock(return_value=0.5)))
        self.assertEqual(loop.stop_reason(args, set(), 0, 6.0, time.time() + 3600), "cost limit ($6.00)")


class TestGhRetry(LoopTest):
    def test_sh_retries_a_failing_gh(self):
        self.env |= {"FAKE_GH_FAIL": "issue edit", "FAKE_GH_FAIL_TIMES": "2"}
        with mock.patch.dict(os.environ, self.env), mock.patch.object(loop.time, "sleep") as sleep:
            loop.sh("gh", "issue", "edit", "1", "--add-label", "x")
        self.assertEqual(sleep.call_count, 2)
        self.assertIn("x", self.labels(1))

    def test_a_gh_hiccup_does_not_end_the_night(self):
        out = self.run_loop("--harness", "pi", "--reviewer", "none",
                            FAKE_GH_FAIL="issue edit 1", FAKE_GH_FAIL_TIMES="1")
        self.assertIn("Stopped: queue empty", out.stdout, out.stderr)
        self.assertIn("overnight:done", self.labels(1))

    def test_writes_that_are_not_idempotent_are_tried_once(self):
        for cmd in (["issue", "comment", "1", "--body", "x"], ["auth", "status"]):
            with mock.patch.dict(os.environ, self.env | {"FAKE_GH_FAIL": " ".join(cmd[:2])}), \
                    mock.patch.object(loop.time, "sleep") as sleep:
                loop.sh("gh", *cmd, check=False)
            sleep.assert_not_called()
        log = Path(str(self.state) + ".log").read_text()
        self.assertEqual((log.count("issue comment"), log.count("auth status")), (1, 1))

    def test_a_gh_that_stays_down_still_gets_a_summary(self):
        out = self.run_loop("--harness", "pi", "--reviewer", "none", no_sleep=True,
                            FAKE_GH_FAIL="issue edit 2")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("Stopped: gh issue edit failed", out.stdout, out.stderr)
        self.assertIn("#1 First", out.stdout)

    def test_a_failed_comment_only_warns(self):
        out = self.run_loop("--harness", "pi", "--reviewer", "none", FAKE_GH_FAIL="issue comment 1")
        self.assertIn("could not comment on #1", out.stdout, out.stderr)
        self.assertIn("Stopped: queue empty", out.stdout, out.stderr)
        self.assertIn("overnight:done", self.labels(1))


class TestInterrupt(LoopTest):
    def interrupt(self, sig: int, mode: str = "hang") -> tuple[str, int]:
        env = self.env | {"FAKE_WORK_1": mode}
        started = 2 if mode == "leftoverhang" else 1
        proc = subprocess.Popen([sys.executable, str(SCRIPT), "--harness", "pi", "--reviewer", "none"],
                                cwd=self.repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            deadline = time.monotonic() + 120
            while len(self.pids.read_text().split()) < started and time.monotonic() < deadline:
                time.sleep(0.1)
            self.assertIn("overnight:working", self.labels(1))
            proc.send_signal(sig)
            out, _ = proc.communicate(timeout=120)
        finally:
            proc.kill()
        time.sleep(0.3)
        for pid in map(int, self.pids.read_text().split()):
            self.assertFalse(alive(pid), f"{pid} outlived the loop")
        self.assertNotIn("overnight:working", self.labels(1))
        self.assertIn("Stopped: interrupted", out)
        return out, proc.returncode

    def test_ctrl_c(self):
        self.interrupt(signal.SIGINT)

    def test_sigterm(self):
        self.interrupt(signal.SIGTERM)

    def test_a_closed_terminal(self):
        self.interrupt(signal.SIGHUP)

    def test_a_server_the_worker_detached_dies_too(self):
        self.interrupt(signal.SIGINT, "leftoverhang")


class TestLeftovers(LoopTest):
    def assert_all_dead(self):
        pids = list(map(int, self.pids.read_text().split()))
        self.assertTrue(pids)
        for pid in pids:
            self.assertFalse(alive(pid), f"{pid} outlived its issue")

    def test_a_detached_server_left_by_a_worker_dies(self):
        out = self.run_loop("--harness", "pi", "--reviewer", "none", FAKE_WORK_1="leftover")
        self.assertIn("overnight:done", self.labels(1), out.stderr)
        self.assert_all_dead()

    def test_a_detached_server_left_by_verify_dies(self):
        # One issue, so no later agent's cleanup hides a missing one after verify.
        self.issues({1: "First"})
        out = self.run_loop("--harness", "pi", "--reviewer", "none", FAKE_WORK_1="verifyleak")
        self.assertIn("overnight:done", self.labels(1), out.stderr)
        self.assert_all_dead()

    def test_a_process_with_a_terminal_is_spared(self):
        self.run_loop("--harness", "pi", "--reviewer", "none", FAKE_WORK_1="terminal")
        spare = int(Path(str(self.pids) + ".spare").read_text())
        try:
            self.assertTrue(alive(spare))
        finally:
            os.kill(spare, signal.SIGKILL)

    def test_a_process_with_a_live_parent_is_spared(self):
        self.run_loop("--harness", "pi", "--reviewer", "none", FAKE_WORK_1="ide")
        spare = int(Path(str(self.pids) + ".spare").read_text())
        self.addCleanup(lambda: alive(spare) and os.kill(spare, signal.SIGKILL))
        self.assertTrue(alive(spare), "a language server's child was killed")

    def test_the_shell_that_started_the_loop_is_spared(self):
        # Started a second before the first agent, from the repo, with no terminal.
        out = subprocess.run(["sh", "-c", f'"{sys.executable}" "{SCRIPT}" --harness pi --reviewer none; echo survived'],
                             cwd=self.repo, env=self.env, capture_output=True, text=True, timeout=60,
                             start_new_session=True)
        self.assertIn("survived", out.stdout, out.stderr)

    def test_reads_ps_elapsed_time(self):
        self.assertEqual(loop.seconds("1-02:03:04"), 93784)
        self.assertEqual(loop.seconds("03:04"), 184)

    def test_claude_workers_cannot_background_tasks(self):
        self.run_loop("--harness", "claude", "--reviewer", "none")
        self.assertEqual(set(Path(str(self.agent_log) + ".env").read_text().split()), {"1"})


class TestBoardSync(unittest.TestCase):
    def test_finds_the_status_field_of_an_organization_board(self):
        board = load("board-sync.py")
        field = {"id": "F", "options": []}
        reply = json.dumps({"data": {"repositoryOwner": {"projectV2": {"id": "P", "field": field}}}})
        with mock.patch.object(board, "gh", return_value=reply) as gh:
            self.assertEqual(board.status_field("some-org", 3), field)
        self.assertIn("repositoryOwner(login: $o)", gh.call_args.args[-1])


class TestGateway(unittest.TestCase):
    def test_an_outage_keeps_the_last_count(self):
        readings = [1.0, 1.5, urllib.error.URLError("down")]
        with mock.patch.object(loop, "cloud_spend", side_effect=readings), mock.patch("builtins.print"):
            spend = loop.RunSpend()
            self.assertEqual(spend.read(), 0.5)
            self.assertEqual(spend.read(), 0.5)


class TestCostLabels(LoopTest):
    def test_claude_phases_are_labelled_list_price(self):
        out = self.run_loop("--harness", "claude", "--reviewer", "none")
        self.assertIn("done: worker claude/default $0.25 list", out.stdout, out.stderr)
        self.assertIn("Real: $0.00. Claude: subscription, $0.50 at list price.", out.stdout)

    def test_real_sums_the_runs_own_phases(self):
        out = self.run_loop("--harness", "pi", "--reviewer", "claude")
        costs = [float(c) for c in re.findall(r"pi/cloud \$([\d.]+)", out.stdout)]
        self.assertEqual(len(costs), 2, out.stdout + out.stderr)
        self.assertIn(f"Real: ~${sum(costs):.2f} DeepSeek", out.stdout)

    def test_the_shared_gateway_counter_is_not_the_real_cost(self):
        # Two lanes share one counter; each reads all of it.
        args = argparse.Namespace(gateway_used=True, spend=mock.Mock(total=27.97, gaps=0))
        self.assertEqual(loop.money_line(args, 15.7, 2.24),
                         "Real: ~$2.24 at DeepSeek's list price, summed from this run's own phases. "
                         "Claude: subscription, $15.70 at list price.")

    def test_a_run_keeps_its_whole_text(self):
        long = "x" * 5000
        self.assertEqual(len(loop.claude_result(json.dumps({"type": "result", "result": long})).text), 5000)
        event = {"type": "message_end", "message": {"role": "assistant", "content": [{"type": "text", "text": long}]}}
        self.assertEqual(len(loop.pi_result(json.dumps(event)).text), 5000)

    def test_the_worker_is_not_told_to_gate_before_starting(self):
        self.assertNotIn("before changing anything", loop.WORKER)


class TestClassifierBlock(LoopTest):
    BLOCKED = "Stopped: the auto mode classifier blocked my edit of tests/test_theme.gd."

    def test_a_blocked_claude_worker_is_retried_on_pi_and_keeps_its_work(self):
        self.issues({1: "First"})
        out = self.run_loop("--harness", "claude", "--reviewer", "none", FAKE_WORK_1="blocked",
                            FAKE_BLOCKED=self.BLOCKED)
        self.assertEqual(self.roles(), ["claude ping", "claude work", "pi work"], out.stdout + out.stderr)
        self.assertIn("overnight:done", self.labels(1), out.stdout + out.stderr)
        log = self.git("log", "--format=%s")
        self.assertIn("feat: first (#1)", log)
        self.assertEqual((self.repo / "second1.txt").read_text(), "left uncommitted\n")
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertIn("blocked: classifier", (self.repo / ".overnight/logs/1.log").read_text())
        self.assertIn("blocked: classifier", self.comments(1)[-1])
        self.assertIn("retry pi/cloud", out.stdout)
        retry = float(re.search(r"retry pi/cloud \$([\d.]+)", out.stdout).group(1))
        self.assertIn(f"Real: ~${retry:.2f} DeepSeek", out.stdout)

    def test_the_retrys_cost_counts_toward_max_cost(self):
        self.issues({1: "First", 2: "Second"})
        out = self.run_loop("--harness", "claude", "--reviewer", "none", "--max-cost", "0.26",
                            FAKE_WORK_1="blocked", FAKE_BLOCKED=self.BLOCKED)
        self.assertIn("Stopped: cost limit", out.stdout, out.stderr)
        self.assertEqual(self.labels(2), ["ready-for-agent"])

    def test_a_budget_is_allowed_for_a_claude_harness(self):
        out = self.run_loop("--harness", "claude", "--reviewer", "none", "--budget", "5")
        self.assertNotIn("--budget counts", out.stderr)

    def test_the_retry_runs_on_the_gateway_model_and_names_the_blocked_edit(self):
        self.issues({1: "First"})
        self.run_loop("--harness", "claude", "--reviewer", "none", FAKE_WORK_1="blocked",
                      FAKE_BLOCKED=self.BLOCKED)
        argv = self.argv_of("pi work")[0]
        self.assertEqual(argv[argv.index("--model") + 1], "cloud")
        self.assertIn("tests/test_theme.gd", Path(str(self.agent_log) + ".prompts").read_text())

    def test_a_retry_that_fails_verify_parks_with_the_reason(self):
        self.issues({1: "First"})
        out = self.run_loop("--harness", "claude", "--reviewer", "none", FAKE_WORK_1="blocked",
                            FAKE_BLOCKED=self.BLOCKED, FAKE_RETRY_BREAKS="1")
        self.assertIn("overnight:parked", self.labels(1), out.stdout + out.stderr)
        self.assertIn("blocked: classifier", self.comments(1)[-1])
        self.assertNotIn("feat: first", self.git("log", "--format=%s"))

    def test_a_claude_result_without_the_text_parks_as_before(self):
        self.issues({1: "First"})
        out = self.run_loop("--harness", "claude", "--reviewer", "none", FAKE_WORK_1="nocommit")
        self.assertIn("overnight:parked", self.labels(1), out.stdout + out.stderr)
        self.assertEqual(self.roles(), ["claude ping", "claude work"])

    def test_a_pi_worker_is_never_retried(self):
        self.issues({1: "First"})
        self.run_loop("--harness", "pi", "--reviewer", "none", FAKE_WORK_1="blocked",
                      FAKE_BLOCKED=self.BLOCKED)
        self.assertEqual(self.roles().count("pi work"), 1)

    def argv_of(self, role: str) -> list[list[str]]:
        return [json.loads(line.split(" ", 2)[2]) for line in self.agent_log.read_text().splitlines()
                if " ".join(line.split()[:2]) == role]


class TestLongPrompt(LoopTest):
    def test_a_prompt_past_the_argument_limit_reaches_the_agent(self):
        self.issues({1: "Huge"}, body="Done when: it works.\n" + "x" * 2_000_000)
        out = self.run_loop("--harness", "pi", "--reviewer", "claude")
        self.assertIn("overnight:done", self.labels(1), out.stderr[-2000:])
        self.assertIn("claude review", self.roles())


class TestIssueComments(LoopTest):
    def test_the_planner_sees_why_an_earlier_run_parked(self):
        state = json.loads(self.state.read_text())
        state["issues"]["1"]["comments"] = ["Parked by the overnight run: the jump test timed out."]
        self.state.write_text(json.dumps(state))
        self.run_loop("--harness", "pi", "--reviewer", "claude")
        self.assertIn("the jump test timed out", Path(str(self.agent_log) + ".prompts").read_text())


class TestLog(LoopTest):
    def test_the_log_skips_streamed_tokens_and_keeps_the_rest(self):
        self.run_loop("--harness", "pi", "--reviewer", "none")
        log = (self.repo / ".overnight" / "logs" / "1.log").read_text()
        self.assertNotIn("message_update", log)
        self.assertIn('"type": "message_end"', log)


class TestCommitSubjects(LoopTest):
    def test_the_summary_names_subjects_that_are_not_conventional(self):
        out = self.run_loop("--harness", "pi", "--reviewer", "none", FAKE_WORK_2="badsubject")
        self.assertIn("Not conventional commits", out.stdout, out.stderr)
        self.assertIn("  Add stuff", out.stdout)
        self.assertNotIn("feat: issue 1", out.stdout.split("Not conventional")[1])
        self.assertNotIn("progress for", out.stdout.split("Not conventional")[1])


class TestBalance(unittest.TestCase):
    def balance(self, model: str | None, dollars: float) -> mock.Mock:
        args = argparse.Namespace(harness="pi", model=model, reviewer="claude", reviewer_model=None)
        with mock.patch.dict(os.environ, {"DEEPSEEK_API_KEY": "k"}), \
                mock.patch.object(loop.preflight, "fetch_balance", return_value=(dollars, "USD")) as fetch:
            loop.check_balance(args)
        return fetch

    def test_a_low_balance_stops_a_direct_deepseek_run(self):
        with self.assertRaises(SystemExit) as e:
            self.balance("deepseek/deepseek-flash", 1.2)
        self.assertIn("$1.20", str(e.exception))

    def test_a_funded_key_starts(self):
        self.balance("deepseek/deepseek-flash", 9.0).assert_called_once()

    def test_the_gateway_is_not_checked(self):
        self.balance(None, 0.0).assert_not_called()


class TestPiEvents(unittest.TestCase):
    def test_reads_errors_only_from_error_events(self):
        quoted = json.dumps({"type": "tool_execution_end", "result": "Insufficient Balance"})
        failed = json.dumps({"type": "message_end", "message": {
            "role": "assistant", "stopReason": "error", "errorMessage": "402 Insufficient Balance"}})
        retry = json.dumps({"type": "auto_retry_end", "finalError": "budget_exceeded"})
        self.assertFalse(loop.pi_result(quoted).broke)
        self.assertTrue(loop.pi_result(failed).broke)
        self.assertTrue(loop.pi_result(retry).broke)

    def test_an_answer_after_a_failed_turn_clears_the_error(self):
        failed = json.dumps({"type": "message_end", "message": {
            "role": "assistant", "stopReason": "error", "errorMessage": "429 Too Many Requests"}})
        answered = json.dumps({"type": "message_end", "message": {
            "role": "assistant", "stopReason": "stop", "content": [{"type": "text", "text": "ok"}]}})
        run = loop.pi_result(failed + "\n" + answered)
        self.assertEqual((run.error, run.text), ("", "ok"))


if __name__ == "__main__":
    unittest.main()
