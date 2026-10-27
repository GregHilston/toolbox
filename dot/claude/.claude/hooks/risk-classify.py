#!/usr/bin/env python3
"""Shadow-mode risk classifier for Bash commands. A Claude Code PreToolUse hook.

Never blocks and prints nothing. Safe commands are logged by rule; the rest go
to the LLM gateway from a detached child, so Claude never waits. Runs only on
moria, so it never loads dungeon. Decisions land in ~/.claude/logs/risk-classify.jsonl.

Not wired into settings.json since 2026-10-27. Nothing read its log (20,927 rows
in six days, most "deny"s false alarms), and its call per command kept moria's
A3B loaded. Re-add it under PreToolUse/Bash to resume the experiment.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HOST = "moria"
LOG = Path.home() / ".claude" / "logs" / "risk-classify.jsonl"
BASE_URL = os.environ.get("RISK_CLASSIFY_BASE_URL", "https://llm.grehg2.xyz/v1")
MODEL = "local-small"
TIMEOUT = 5

READ_ONLY = {
    "ls", "pwd", "cat", "head", "tail", "wc", "grep", "rg", "find", "which", "whoami",
    "echo", "date", "stat", "file", "du", "df", "tree", "diff", "uname", "hostname",
}
GIT_READ = {"status", "diff", "log", "show", "branch", "remote", "rev-parse", "ls-files", "blame", "describe"}
GH_READ = {("pr", "view"), ("pr", "list"), ("pr", "diff"), ("pr", "checks"), ("pr", "status"),
           ("issue", "view"), ("issue", "list"), ("run", "view"), ("run", "list")}
# Chaining, substitution or redirection can hide a second command.
SHELL_META = re.compile(r"[;&|<>`\n]|\$\(")
FIND_WRITES = {"-delete", "-exec", "-execdir", "-ok", "-fprint"}

PROMPT = (
    "You review one shell command an AI coding agent is about to run. Reply with "
    "exactly one word, allow, ask or deny, then a colon and a one-line reason. "
    "allow: read-only or easily undone. ask: deletes, overwrites, pushes, installs, "
    "uses the network or sudo, or you are unsure. deny: destructive and irreversible "
    "(rm -rf on home or root, force push to main, disk wipes, credential exfiltration)."
)


def allowed_by_rule(command: str) -> bool:
    command = command.strip().replace("2>&1", "").replace("2>/dev/null", "")
    if not command or SHELL_META.search(command):
        return False
    words = command.split()
    head = words[0]
    if head in READ_ONLY:
        return not (head == "find" and FIND_WRITES & set(words))
    if head == "git":
        rest = [w for w in words[1:] if w != "--no-pager"]
        return bool(rest) and rest[0] in GIT_READ and not (
            rest[0] == "branch" and any(not w.startswith("-") or w in ("-d", "-D", "-m", "-M") for w in rest[1:])
        )
    if head == "gh":
        return tuple(words[1:3]) in GH_READ
    return False


def classify(command: str, api_key: str) -> tuple[str, str]:
    """Returns (decision, source); anything unusable is an ask."""
    body = {
        "model": MODEL,
        "temperature": 0,
        "max_tokens": 40,
        "chat_template_kwargs": {"enable_thinking": False},
        "messages": [{"role": "system", "content": PROMPT}, {"role": "user", "content": command[:2000]}],
    }
    req = urllib.request.Request(
        f"{BASE_URL.rstrip('/')}/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            text = json.load(resp)["choices"][0]["message"]["content"] or ""
    except Exception:
        return "ask", "error"
    match = re.match(r"\W*(allow|ask|deny)\b", text.strip().lower())
    return (match.group(1), "model") if match else ("ask", "error")


def log(event: dict, decision: str, source: str, started: float) -> None:
    row = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "cwd": event.get("cwd", ""),
        "command": event["tool_input"]["command"],
        "decision": decision,
        "source": source,
        "latency_ms": round((time.monotonic() - started) * 1000),
    }
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps(row) + "\n")


def child() -> None:
    started = time.monotonic()
    event = json.load(sys.stdin)
    key = os.environ.get("LITELLM_API_KEY", "")
    decision, source = classify(event["tool_input"]["command"], key) if key else ("ask", "error")
    log(event, decision, source, started)


def main() -> None:
    if socket.gethostname().split(".")[0].lower() != HOST:
        return
    started = time.monotonic()
    raw = sys.stdin.read()
    event = json.loads(raw)
    if allowed_by_rule(event["tool_input"]["command"]):
        log(event, "allow", "rule", started)
        return
    proc = subprocess.Popen(
        [sys.executable, __file__, "--child"],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    proc.stdin.write(raw.encode())
    proc.stdin.close()


if __name__ == "__main__":
    try:
        child() if sys.argv[1:] == ["--child"] else main()
    except Exception:  # shadow mode must never fail a command
        pass
    sys.exit(0)
