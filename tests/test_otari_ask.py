"""otari-ask.py runs a read-only DeepSeek worker on Otari; these check what it asks claude for.

A fake `claude` on PATH records its argv, cwd and environment and prints
canned stream-json events, so nothing touches the network or a real model.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "bin" / "otari-ask.py"

FAKE_CLAUDE = textwrap.dedent("""\
    #!/usr/bin/env python3
    import json, os, sys, time
    # The worker's env is minimal, so setup comes from a file.
    cfg = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake.json")))
    keep = ("ANTHROPIC_", "CLAUDE_CODE_", "HERDR_", "DEEPSEEK_", "OTARI_")
    with open(cfg["FAKE_CLAUDE_LOG"], "a") as f:
        f.write(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd(), "home": os.environ.get("HOME"),
                            "env": {k: v for k, v in os.environ.items() if k.startswith(keep)}}) + "\\n")
    for line in cfg.get("FAKE_CLAUDE_OUT", "").splitlines():
        sys.stdout.write(line + "\\n")
        sys.stdout.flush()
    time.sleep(float(cfg.get("FAKE_CLAUDE_SLEEP", "0")))
    sys.exit(int(cfg.get("FAKE_CLAUDE_EXIT", "0")))
""")


def stream(*events: dict) -> str:
    return "\n".join(json.dumps(e) for e in events)


INIT = {"type": "system", "subtype": "init", "session_id": "sess-1"}
TOOL = {"type": "assistant", "message": {"id": "m1", "usage": {"input_tokens": 0}, "content": [
    {"type": "tool_use", "name": "Read", "input": {"file_path": "src/gate.ts"}}]}}
DELTA = {"type": "stream_event", "event": {"type": "message_delta", "usage": {
    "input_tokens": 1000, "output_tokens": 10, "cost_usd": "0.0123"}}}
TEXT_DELTA = {"type": "stream_event", "event": {"type": "content_block_delta",
                                                "delta": {"type": "text_delta", "text": "No premium "}}}
TEXT_DELTA_2 = {"type": "stream_event", "event": {"type": "content_block_delta",
                                                  "delta": {"type": "text_delta", "text": "gate remains."}}}
ANSWER = {"type": "assistant", "message": {"id": "m2", "content": [
    {"type": "text", "text": "No premium gate remains."}]}}
RESULT = {"type": "result", "subtype": "success", "is_error": False, "num_turns": 7,
          "result": "No premium gate remains.", "session_id": "sess-1"}
THINKING = {"type": "system", "subtype": "thinking_tokens", "estimated_tokens": 840}
OK = stream(INIT, TOOL, DELTA, TEXT_DELTA, TEXT_DELTA_2, ANSWER, RESULT)


class TestOtariAsk(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.bin = root / "bin"
        self.bin.mkdir()
        claude = self.bin / "claude"
        claude.write_text(FAKE_CLAUDE)
        claude.chmod(0o755)
        self.repo = root / "repo"
        (self.repo / ".claude").mkdir(parents=True)
        (self.repo / ".claude" / "CLAUDE.md").write_text("Use vitest.\n")
        self.calls = root / "calls.jsonl"
        self.cache = root / "cache"
        self.env = {"PATH": f"{self.bin}:/usr/bin:/bin", "HOME": str(root),
                    "OTARI_ASK_CACHE": str(self.cache), "TOOLBOX_HOME": str(root / "toolbox"),
                    "OTARI_API_KEY": "otk_test", "FAKE_CLAUDE_LOG": str(self.calls), "FAKE_CLAUDE_OUT": OK}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def fake(self, env: dict) -> dict:
        """Write the fake claude's setup; return the env without it."""
        (self.bin / "fake.json").write_text(json.dumps({k: v for k, v in env.items() if k.startswith("FAKE_")}))
        return {k: v for k, v in env.items() if not k.startswith("FAKE_")}

    def popen(self, *args: str, **env: str) -> subprocess.Popen:
        return subprocess.Popen(["python3", str(SCRIPT), *args], env=self.fake({**self.env, **env}),
                                stdout=subprocess.PIPE, text=True)

    def ask(self, *args: str, **env: str) -> subprocess.CompletedProcess:
        return subprocess.run(["python3", str(SCRIPT), *args], env=self.fake({**self.env, **env}),
                              capture_output=True, text=True, timeout=60)

    def first(self, *extra: str, **env: str) -> subprocess.CompletedProcess:
        return self.ask("--session", "inv-1", "--dir", str(self.repo), *extra, "where is the gate?", **env)

    def last_call(self) -> dict:
        return json.loads(self.calls.read_text().splitlines()[-1])

    def settings(self) -> dict:
        argv = self.last_call()["argv"]
        return json.loads(Path(argv[argv.index("--settings") + 1]).read_text())

    def test_first_turn_runs_sandboxed_on_otari(self):
        out = self.first()
        self.assertEqual(out.returncode, 0, out.stderr)
        call = self.last_call()
        argv = call["argv"]
        self.assertNotIn("--bare", argv)
        self.assertEqual(argv[argv.index("--setting-sources") + 1], "")
        self.assertIn("--strict-mcp-config", argv)
        self.assertEqual(argv[argv.index("--permission-mode") + 1], "dontAsk")
        self.assertEqual(argv[argv.index("--tools") + 1], "Read,Bash")
        self.assertIn(f"Read(/{self.repo.resolve()}/**)", argv)
        self.assertIn("--session-id", argv)
        self.assertEqual(argv[-2:], ["--", "where is the gate?"])
        self.assertEqual(Path(call["cwd"]).resolve(), self.repo.resolve())
        env = call["env"]
        self.assertEqual(env["ANTHROPIC_BASE_URL"], "https://api.otari.ai/api")
        self.assertEqual(env["ANTHROPIC_API_KEY"], "otk_test")
        self.assertEqual(env["ANTHROPIC_MODEL"], "deepseek/deepseek-v4.1-flash")
        self.assertEqual(env["ANTHROPIC_DEFAULT_HAIKU_MODEL"], env["ANTHROPIC_MODEL"])
        self.assertIn("Otari-Tags: agent=otari-ask,run=inv-1", env["ANTHROPIC_CUSTOM_HEADERS"])
        self.assertNotIn("Otari-Web-Search", env["ANTHROPIC_CUSTOM_HEADERS"])

    def test_the_worker_gets_its_own_home(self):
        self.first()
        self.assertEqual(Path(self.last_call()["home"]), self.cache / "home")

    def test_the_sandbox_reads_only_the_repo_and_hides_secrets(self):
        (self.repo / ".env.local").write_text("K=v\n")
        (self.repo / ".env.example").write_text("K=\n")
        (self.repo / "config").mkdir()
        (self.repo / "config" / "server.pem").write_text("x\n")
        self.first()
        sandbox = self.settings()["sandbox"]
        self.assertTrue(sandbox["enabled"] and sandbox["failIfUnavailable"])
        self.assertFalse(sandbox["allowUnsandboxedCommands"])
        fs = sandbox["filesystem"]
        self.assertEqual(fs["denyRead"], ["//"])
        self.assertIn(f"/{self.repo.resolve()}", fs["allowRead"])
        self.assertEqual(fs["denyWrite"], [f"/{self.repo.resolve()}"])
        hidden = {f["path"] for f in sandbox["credentials"]["files"]}
        self.assertEqual(hidden, {str(self.repo.resolve() / ".env.local"), str(self.repo.resolve() / "config" / "server.pem")})
        self.assertIn("ANTHROPIC_API_KEY", {v["name"] for v in sandbox["credentials"]["envVars"]})
        self.assertEqual(sandbox["network"]["allowedDomains"], [])
        self.assertIn(f"Read(/{self.repo.resolve() / '.env.local'})", self.settings()["permissions"]["deny"])

    def test_web_adds_search_fetch_and_the_otari_header(self):
        self.first("--web")
        argv = self.last_call()["argv"]
        self.assertEqual(argv[argv.index("--tools") + 1], "Read,Bash,WebSearch,WebFetch")
        self.assertIn("Otari-Web-Search: otari", self.last_call()["env"]["ANTHROPIC_CUSTOM_HEADERS"])
        self.assertIn("WebFetch(domain:*.ts.net)", self.settings()["permissions"]["deny"])
        brief = Path(argv[argv.index("--append-system-prompt-file") + 1]).read_text()
        self.assertIn("untrusted", brief)

    def test_a_web_session_keeps_web_on_follow_up(self):
        self.first("--web")
        self.ask("--session", "inv-1", "more")
        self.assertIn("WebSearch", self.last_call()["argv"])

    def test_web_searches_are_costed(self):
        search = {"type": "assistant", "message": {"id": "m3", "content": [
            {"type": "tool_use", "name": "WebSearch", "input": {"query": "q"}}]}}
        out = self.first("--web", FAKE_CLAUDE_OUT=stream(INIT, search, DELTA, ANSWER, RESULT))
        self.assertIn("1 searches", out.stdout)
        self.assertIn("$0.0223", out.stdout)

    def test_no_dir_means_an_empty_scratch_dir(self):
        out = self.ask("--session", "web-1", "--web", "q")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(Path(self.last_call()["cwd"]).resolve(), (self.cache / "scratch" / "web-1").resolve())

    def test_home_as_dir_is_refused(self):
        out = self.ask("--session", "h", "--dir", self.env["HOME"], "q")
        self.assertEqual(out.returncode, 2)
        self.assertIn("whole home", out.stderr)
        self.assertFalse(self.calls.exists())

    def test_a_remote_with_a_password_is_refused(self):
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin", "https://me:tok3n@github.com/x/y"],
                       check=True)
        out = self.first()
        self.assertEqual(out.returncode, 2)
        self.assertIn("password in its URL", out.stderr)

    def test_model_flag_reaches_every_alias(self):
        self.first("--model", "deepseek/deepseek-v4-pro")
        env = self.last_call()["env"]
        self.assertEqual(env["ANTHROPIC_MODEL"], "deepseek/deepseek-v4-pro")
        self.assertEqual(env["CLAUDE_CODE_SUBAGENT_MODEL"], "deepseek/deepseek-v4-pro")

    def test_prints_the_answer_otari_cost_and_follow_up(self):
        out = self.first()
        self.assertIn("No premium gate remains.", out.stdout)
        self.assertIn("7 turns", out.stdout)
        self.assertIn("$0.0123 on Otari", out.stdout)
        self.assertIn('otari-ask.py --session inv-1 "..."', out.stdout)

    def test_narration_and_events_are_logged(self):
        self.first()
        log = (self.cache / "inv-1.log").read_text()
        self.assertIn("→ Read src/gate.ts", log)
        events = (self.cache / "inv-1.jsonl").read_text()
        self.assertIn("message_delta", events)
        self.assertNotIn("content_block_delta", events)

    def test_agents_md_reaches_the_worker(self):
        (self.repo / "AGENTS.md").write_text("Use vitest.\n")
        self.first()
        argv = self.last_call()["argv"]
        brief = Path(argv[argv.index("--append-system-prompt-file") + 1]).read_text()
        self.assertIn("headless, read-only worker", brief)
        self.assertIn("sandboxed", brief)
        self.assertIn("Use vitest.", brief)

    def test_a_follow_up_resumes_in_the_first_turns_repo(self):
        self.first()
        out = self.ask("--session", "inv-1", "and why?")
        self.assertEqual(out.returncode, 0, out.stderr)
        call = self.last_call()
        self.assertEqual(call["argv"][call["argv"].index("--resume") + 1], "sess-1")
        self.assertEqual(Path(call["cwd"]).resolve(), self.repo.resolve())

    def test_a_follow_up_in_another_repo_is_refused(self):
        self.first()
        out = self.ask("--session", "inv-1", "--dir", self.tmp.name, "q")
        self.assertEqual(out.returncode, 2)
        self.assertIn("start a new --session", out.stderr)

    def test_reads_the_key_from_the_work_secrets_file(self):
        secrets = Path(self.env["TOOLBOX_HOME"]) / "nixos" / "secrets"
        secrets.mkdir(parents=True)
        (secrets / "work.env").write_text("OTARI_API_KEY='otk_file'\n")
        env = dict(self.env)
        env.pop("OTARI_API_KEY")
        out = subprocess.run(["python3", str(SCRIPT), "--session", "k", "--dir", str(self.repo), "q"],
                             env=self.fake(env), capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(self.last_call()["env"]["ANTHROPIC_API_KEY"], "otk_file")

    def test_no_key_anywhere_says_how_to_get_one(self):
        env = dict(self.env)
        env.pop("OTARI_API_KEY")
        out = subprocess.run(["python3", str(SCRIPT), "--session", "k", "q"], env=self.fake(env),
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 2)
        self.assertIn("just secrets", out.stderr)
        self.assertFalse(self.calls.exists(), "claude never ran")

    def test_only_a_minimal_env_reaches_the_worker(self):
        self.first(ANTHROPIC_AUTH_TOKEN="personal", DEEPSEEK_API_KEY="sk", HERDR_PANE="1", OTARI_API_KEY="otk_test")
        env = self.last_call()["env"]
        for k in ("ANTHROPIC_AUTH_TOKEN", "DEEPSEEK_API_KEY", "HERDR_PANE"):
            self.assertNotIn(k, env)

    def test_a_worker_error_exits_1_and_prints_it(self):
        failed = {**RESULT, "is_error": True, "result": "API Error: 403 budget_exceeded"}
        out = self.first(FAKE_CLAUDE_OUT=stream(INIT, failed))
        self.assertEqual(out.returncode, 1)
        self.assertIn("the worker failed: API Error: 403 budget_exceeded", out.stdout)

    def test_no_result_and_a_bad_exit_is_a_failure(self):
        out = self.first(FAKE_CLAUDE_OUT="boom", FAKE_CLAUDE_EXIT="3")
        self.assertEqual(out.returncode, 1)
        self.assertIn("claude exited 3", out.stdout)

    def test_over_max_cost_stops_with_4(self):
        out = self.first("--max-cost", "0.01", FAKE_CLAUDE_SLEEP="30")
        self.assertEqual(out.returncode, 4, out.stdout)
        self.assertIn("over --max-cost", out.stdout)

    def test_max_turns_result_exits_4(self):
        capped = {**RESULT, "subtype": "error_max_turns", "is_error": True, "result": ""}
        out = self.first(FAKE_CLAUDE_OUT=stream(INIT, capped))
        self.assertEqual(out.returncode, 4)
        self.assertIn("over --max-turns", out.stdout)

    def test_a_silent_worker_is_killed_with_3(self):
        started = time.monotonic()
        out = self.first("--idle", "1", FAKE_CLAUDE_OUT=stream(INIT), FAKE_CLAUDE_SLEEP="60")
        self.assertEqual(out.returncode, 3, out.stdout)
        self.assertLess(time.monotonic() - started, 30)

    def test_sigterm_stops_the_worker(self):
        proc = self.popen("--session", "inv-1", "--dir", str(self.repo), "q",
                          FAKE_CLAUDE_OUT=stream(INIT), FAKE_CLAUDE_SLEEP="60")
        proc.stdout.readline()  # the start line: claude is running
        os.kill(proc.pid, signal.SIGTERM)
        self.assertEqual(proc.wait(timeout=30), 128 + signal.SIGTERM)
        proc.stdout.close()

    def test_a_running_session_is_refused_with_5(self):
        proc = self.popen("--session", "inv-1", "--dir", str(self.repo), "q",
                          FAKE_CLAUDE_OUT=stream(INIT), FAKE_CLAUDE_SLEEP="60")
        try:
            proc.stdout.readline()
            out = self.ask("--session", "inv-1", "q")
            self.assertEqual(out.returncode, 5)
        finally:
            proc.terminate()
            proc.wait(timeout=30)
            proc.stdout.close()

    def test_no_session_names_one(self):
        out = self.ask("q")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertRegex(out.stdout, r'--session ask-\d{4}-\d{6} "\.\.\."')
        self.assertTrue(list(self.cache.glob("ask-*.json")))

    def test_a_pipe_gets_only_the_answer(self):
        out = self.first()
        self.assertNotIn("→", out.stdout)
        self.assertIn("=== answer (inv-1", out.stdout)

    def test_no_dir_turns_web_on(self):
        self.ask("--session", "w", "q")
        argv = self.last_call()["argv"]
        self.assertIn("WebSearch", argv[argv.index("--tools") + 1])
        self.first()
        argv = self.last_call()["argv"]
        self.assertEqual(argv[argv.index("--tools") + 1], "Read,Bash")

    def test_the_log_skips_thinking_tokens(self):
        out = self.ask("--session", "t", "q", FAKE_CLAUDE_OUT=stream(INIT, THINKING, DELTA, ANSWER, RESULT))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertNotIn("thinking_tokens", (self.cache / "t.jsonl").read_text())

    def test_no_repo_tells_the_worker_not_to_explore(self):
        self.ask("--session", "w", "q")
        argv = self.last_call()["argv"]
        brief = Path(argv[argv.index("--append-system-prompt-file") + 1]).read_text()
        self.assertIn("Do not explore", brief)
        self.assertNotIn("working directory is the repo", brief)
        self.first()
        argv = self.last_call()["argv"]
        brief = Path(argv[argv.index("--append-system-prompt-file") + 1]).read_text()
        self.assertIn("working directory is the repo", brief)

    def test_a_bad_name_is_refused(self):
        out = self.ask("--session", "../etc", "q")
        self.assertEqual(out.returncode, 2)
        self.assertFalse(self.calls.exists())


if __name__ == "__main__":
    unittest.main()
