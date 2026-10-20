#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Rerun realistic headless pi chats and check pi still behaves.

Run it after changing pi config, AGENTS.md, skills or tools. Each case in
pi-eval-cases.toml (next to this script) is one `pi -p` chat on the local
model; checks read the transcript, never the live data.

Checks (all optional; regex lists are ANDed, use `|` for either):
    uses_tool         tool names that must appear (read, bash, grep ...)
    not_tool          tool names that must not appear
    bash_matches      regexes each matching some bash command
    not_bash_matches  regexes matching no bash command
    calls_match       regexes each matching some tool call (bash, read, grep)
    reads_skill       skill names whose <skill>/SKILL.md was read
    answer_matches    regexes the final answer must match
    answer_not_matches  regexes it must not match
    max_turns, max_seconds

Usage:
    pi-eval.py                       # all cases, 4 at a time
    pi-eval.py --only sabnzbd-down,front-door
    pi-eval.py --model litellm/local-small --keep ./runs --json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CASES = Path(__file__).resolve().with_name("pi-eval-cases.toml")
DEFAULT_MODEL = "litellm/local-small"
TIMEOUT = 600
# Applies to every case; the suite must never write anywhere.
NEVER_BASH = [r"\bgit (commit|push)\b"]


def parse_transcript(lines) -> dict:
    """Reduce a `--mode json` event stream to calls, answer and turn count."""
    messages: list[dict] = []
    for line in lines:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "agent_end":
            messages = event.get("messages", [])
    calls, answer, turns, error = [], "", 0, ""
    for m in messages:
        if m.get("role") != "assistant":
            continue
        turns += 1
        text = ""
        for c in m.get("content", []):
            if c.get("type") == "toolCall":
                calls.append({"name": c["name"], "args": c.get("arguments") or {}})
            elif c.get("type") == "text":
                text += c.get("text", "")
        if text.strip():
            answer = text.strip()
        if m.get("stopReason") not in ("stop", "toolUse"):
            error = f"{m.get('stopReason')} {m.get('errorMessage', '')}".strip()
    return {"ended": bool(messages), "calls": calls, "answer": answer, "turns": turns, "error": error}


def call_text(call: dict) -> str:
    args = call["args"]
    main = args.get("command") or args.get("path") or json.dumps(args)
    return f"{call['name']} {main}"


def evaluate(t: dict, secs: float, case: dict) -> list[str]:
    """Return one message per failed check; empty means pass."""
    if not t["ended"]:
        return ["pi produced no agent_end"]
    fails = []
    if t["error"]:
        fails.append(f"stopped: {t['error']}")
    names = {c["name"] for c in t["calls"]}
    bash = [str(c["args"].get("command", "")) for c in t["calls"] if c["name"] == "bash"]
    texts = [call_text(c) for c in t["calls"]]
    reads = [str(c["args"].get("path", "")) for c in t["calls"] if c["name"] == "read"]

    for n in case.get("uses_tool", []):
        if n not in names:
            fails.append(f"no {n} call")
    for n in case.get("not_tool", []):
        if n in names:
            fails.append(f"used {n}")
    for rx in case.get("bash_matches", []):
        if not any(re.search(rx, b) for b in bash):
            fails.append(f"no bash matching /{rx}/")
    for rx in case.get("not_bash_matches", []) + NEVER_BASH:
        if any(re.search(rx, b) for b in bash):
            fails.append(f"bash matched forbidden /{rx}/")
    for rx in case.get("calls_match", []):
        if not any(re.search(rx, s) for s in texts):
            fails.append(f"no call matching /{rx}/")
    for skill in case.get("reads_skill", []):
        if not any(p.endswith(f"/{skill}/SKILL.md") for p in reads):
            fails.append(f"did not read {skill} skill")
    for rx in case.get("answer_matches", []):
        if not re.search(rx, t["answer"]):
            fails.append(f"answer lacks /{rx}/")
    for rx in case.get("answer_not_matches", []):
        if re.search(rx, t["answer"]):
            fails.append(f"answer has /{rx}/")
    if "max_turns" in case and t["turns"] > case["max_turns"]:
        fails.append(f"{t['turns']} turns > {case['max_turns']}")
    if "max_seconds" in case and secs > case["max_seconds"]:
        fails.append(f"{secs:.0f}s > {case['max_seconds']}s")
    return fails


def run_case(case: dict, model: str, keep: Path | None) -> dict:
    cwd = os.path.expanduser(case.get("cwd", "~"))
    start = time.monotonic()
    out, code = "", None
    try:
        # stdin must be /dev/null or pi hangs; depth 1 makes bash-guard hard-block.
        p = subprocess.run(
            ["pi", "--mode", "json", "-p", "--approve", "--no-session",
             "--model", model, "--", case["prompt"]],
            cwd=cwd, env={**os.environ, "PI_SUBAGENT_DEPTH": "1"},
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=TIMEOUT,
        )
        out, code = p.stdout, p.returncode
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
    except OSError as e:
        return {"name": case["name"], "pass": False, "secs": 0, "turns": 0, "fails": [str(e)]}
    secs = time.monotonic() - start
    if keep:
        (keep / f"{case['name']}.jsonl").write_text(out)
    t = parse_transcript(out.splitlines())
    fails = evaluate(t, secs, case)
    if not t["ended"] and code is None:
        fails = [f"timed out after {TIMEOUT}s"]
    return {"name": case["name"], "pass": not fails, "secs": round(secs), "turns": t["turns"], "fails": fails}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--only", help="comma-separated case names")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--keep", type=Path, help="directory for raw jsonl transcripts")
    ap.add_argument("--cases", type=Path, default=CASES)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cases = tomllib.loads(args.cases.read_text())["case"]
    if args.only:
        want = set(args.only.split(","))
        unknown = want - {c["name"] for c in cases}
        if unknown:
            print(f"unknown case: {', '.join(sorted(unknown))}", file=sys.stderr)
            return 2
        cases = [c for c in cases if c["name"] in want]
    if args.keep:
        args.keep.mkdir(parents=True, exist_ok=True)

    results = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for r in pool.map(lambda c: run_case(c, args.model, args.keep), cases):
            results.append(r)
            if not args.json:
                status = "PASS" if r["pass"] else "FAIL"
                why = "  " + "; ".join(r["fails"]) if r["fails"] else ""
                print(f"{status}  {r['secs']:>4}s  {r['turns']:>2}t  {r['name']}{why}", flush=True)
    failed = [r for r in results if not r["pass"]]
    if args.json:
        print(json.dumps({"model": args.model, "results": results}, indent=2))
    else:
        print(f"{len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
