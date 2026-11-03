#!/usr/bin/env python3
"""Time a pi worker's commands and LLM turns, from its JSON event stream.

    steptime.py <log>     # print the steps one JSON line each

A step is {"type": "step", "step": "llm"|"cmd", "seconds": s, "t": start,
"cmd": ..., "exit": code, "cat": category}, plus "hung": true when pi's tool timeout
killed the command. `t` is epoch seconds and, for a
command, the end of the turn that asked for it: pi stamps no tool events.
"""

from __future__ import annotations

import json
import re
import sys

# First match wins: a gate runs the tests, a sweep may call the test script.
CATEGORIES = [
    ("gates", re.compile(r"verify\.sh|gate_lanes|tools/quick\.sh")),
    ("sweeps", re.compile(r"sweep\.py|tune\.py|balance_guard|golden_corpus|client_corpus|regen_goldens|sim\.sh|client_sim")),
    ("test runs", re.compile(r"pytest|tools/test\.sh|run_tests\.sh|gut|unittest|godot\b.*\btest|node --test")),
]
TIMEOUT = re.compile(r"Command timed out after \d+ seconds")
EXIT = re.compile(r'"exit_code":\s*(-?\d+)')


def categorise(cmd: str) -> str:
    for name, pattern in CATEGORIES:
        if pattern.search(cmd):
            return name
    return "other commands"


def steps(text: str) -> list[dict]:
    """The pi events in text, as step lines; anything else in text is skipped."""
    out: list[dict] = []
    asked: dict[str, tuple[str, float]] = {}
    turn_end = 0.0
    for line in text.splitlines():
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        kind, msg = event.get("type"), event.get("message") or {}
        if kind == "step":
            out.append(event)
        elif kind == "message_end" and msg.get("role") == "assistant" and msg.get("durationMs") is not None:
            seconds = float(msg["durationMs"]) / 1000
            turn_end = float(msg.get("timestamp") or 0) / 1000 + seconds
            out.append({"type": "step", "step": "llm", "seconds": round(seconds, 3), "t": turn_end - seconds})
        elif kind == "tool_execution_start" and event.get("toolName") == "bash":
            asked[event["toolCallId"]] = (str((event.get("args") or {}).get("command", "")), turn_end)
        elif kind == "tool_execution_end" and event.get("toolCallId") in asked:
            cmd, began = asked.pop(event["toolCallId"])
            found = EXIT.search(json.dumps(event.get("result")))
            code = int(found.group(1)) if found else (1 if event.get("isError") else 0)
            step = {"type": "step", "step": "cmd", "seconds": round(float(event.get("durationMs") or 0) / 1000, 3),
                    "t": began, "cmd": cmd[:300], "exit": code, "cat": categorise(cmd)}
            if event.get("isError") and TIMEOUT.search(json.dumps(event.get("result"))):
                step["hung"] = True
            out.append(step)
    return out


def lines(found: list[dict]) -> str:
    return "".join(json.dumps(s, separators=(",", ":")) + "\n" for s in found)


if __name__ == "__main__":
    sys.stdout.write(lines(steps(open(sys.argv[1], errors="replace").read())))
