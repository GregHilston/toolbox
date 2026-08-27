#!/usr/bin/env python3
"""A stand-in for `pi --mode rpc`, so the supervisor's lifecycle is testable.

`pi-rpc.py` owns three threads, a subprocess and a socket, and every serious
defect found in review lived in how those interact — a shutdown that deadlocked
on a wedged write, a log whose tail was lost to daemon threads, a healthy worker
killed because an ack was slow. None of that is reachable through the pure
functions, and all of it is reachable with a process that speaks the protocol
badly on purpose.

Behaviour is set by environment variables so a test can ask for one failure at a
time:

    FAKE_PI_TURNS          how many turn/tool events to emit before settling (default 2)
    FAKE_PI_ACK_PROMPT     0 to accept the prompt but never send its response
    FAKE_PI_SETTLE         0 to exit without ever emitting agent_settled
    FAKE_PI_STDERR_LINES   how many lines to write to stderr before exiting
    FAKE_PI_IGNORE_STDIN   1 to stop reading stdin entirely, wedging writers
    FAKE_PI_HANG           1 to ignore stdin close and keep running
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time


def env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def emit(event: dict) -> None:
    sys.stdout.write(json.dumps(event) + "\n")
    sys.stdout.flush()


def main() -> int:
    turns = env_int("FAKE_PI_TURNS", 2)
    ack = env_int("FAKE_PI_ACK_PROMPT", 1)
    settle = env_int("FAKE_PI_SETTLE", 1)
    stderr_lines = env_int("FAKE_PI_STDERR_LINES", 0)
    ignore_stdin = env_int("FAKE_PI_IGNORE_STDIN", 0)
    hang = env_int("FAKE_PI_HANG", 0)

    emit({"type": "session", "id": "fake", "cwd": os.getcwd()})

    done = threading.Event()
    steers: list[str] = []

    def run_agent() -> None:
        emit({"type": "agent_start"})
        for turn in range(1, turns + 1):
            emit({"type": "turn_start"})
            emit(
                {
                    "type": "tool_execution_start",
                    "toolCallId": f"c{turn}",
                    "toolName": "bash",
                    "args": {"command": f"echo {turn}"},
                }
            )
            emit(
                {
                    "type": "tool_execution_end",
                    "toolCallId": f"c{turn}",
                    "toolName": "bash",
                    "isError": False,
                    "result": {"content": [{"type": "text", "text": str(turn)}]},
                }
            )
            emit({"type": "turn_end", "message": {"usage": {"cost": {"total": 0.001}}}})
            time.sleep(0.05)
        for line in range(stderr_lines):
            print(f"fake-pi stderr line {line}", file=sys.stderr)
        sys.stderr.flush()
        emit({"type": "agent_end", "messages": [], "willRetry": False})
        if settle:
            emit({"type": "agent_settled"})
            done.set()
            return
        # No settle means "this worker died": exit outright rather than sitting
        # in the stdin loop, which is a hang, not a death, and would leave the
        # supervisor legitimately waiting forever.
        done.set()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)

    if ignore_stdin:
        # Never drain stdin. A large enough write from the supervisor blocks in
        # the pipe, which is the shape that used to deadlock its shutdown.
        threading.Thread(target=run_agent, daemon=True).start()
        done.wait(timeout=30)
        while hang:
            time.sleep(0.1)
        return 0

    started = False
    for raw in sys.stdin.buffer:
        try:
            command = json.loads(raw.decode("utf-8"))
        except ValueError:
            continue
        kind = command.get("type")
        if kind == "prompt" and not started:
            started = True
            if ack:
                emit({"type": "response", "id": command.get("id"), "command": "prompt", "success": True})
            threading.Thread(target=run_agent, daemon=True).start()
        elif kind == "steer":
            steers.append(command.get("message", ""))
            emit({"type": "response", "id": command.get("id"), "command": "steer", "success": True})
        elif kind == "get_state":
            emit(
                {
                    "type": "response",
                    "id": command.get("id"),
                    "command": "get_state",
                    "success": True,
                    "data": {"isStreaming": not done.is_set(), "steers": steers},
                }
            )
        elif kind == "abort":
            emit({"type": "response", "id": command.get("id"), "command": "abort", "success": True})
            done.set()
        else:
            emit(
                {
                    "type": "response",
                    "id": command.get("id"),
                    "command": kind,
                    "success": False,
                    "error": f"fake pi does not implement {kind}",
                }
            )

    # stdin closed: the supervisor is shutting us down.
    done.wait(timeout=10)
    while hang:
        time.sleep(0.1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
