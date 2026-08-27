#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Turn pi's `--mode json` event stream into one readable line per thing that happened.

Why this exists: an orchestrator spawning `pi ... > log.jsonl 2>&1` in the
background throws the entire stream away. Claude Code captures a background
command's output from a PTY, so a full redirect to a file means the harness sees
**zero bytes** and the task row reads "no output available" for the whole run.
The information was never missing — pi emits a rich, line-buffered event stream
in `--mode json` — it was being swallowed by our own redirect.

So put this in the pipe instead of the redirect:

    pi --mode json ... | pi-narrate.py --label issue-16 --raw log.jsonl

It writes the raw JSONL to `--raw` itself, so `tee` is not needed, and emits a
compact narration on stdout. The harness then shows the most recent line as the
task's status, and the full narration is readable at any time.

`--alerts` appends the small subset worth interrupting a human over — tool
failures, guardrail blocks, retries, compaction, completion — to a **shared**
file across all workers in a run, which is what a `tail -F` monitor should
watch. The full narration is far too chatty for that (~150 lines per worker).

Usage:
    pi --mode json -p "$(cat prompt.md)" 2>&1 \\
      | pi-narrate.py --label issue-16 --raw .claude/pi-logs/issue-16.jsonl \\
                      --alerts .claude/pi-logs/alerts.log

    pi-narrate.py --label replay < old.jsonl     # replay a finished log

Note: put `set -o pipefail` in front of the pipeline, or the shell reports this
script's exit status and pi's failure disappears.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, BinaryIO, TextIO

# Tool arguments worth showing, in the order we prefer them. A tool call is only
# useful in a status line if you can see *what* it acted on.
ARG_KEYS = ("command", "path", "file_path", "pattern", "query", "url")

# Events that mean "a human might want to know right now". Everything else is
# narration you read when you go looking.
ALERT_SYMBOLS = frozenset({"✗", "■", "⚠", "!"})


def brief(tool: str, args: Any) -> str:
    """One line describing what a tool call is about to do."""
    if not isinstance(args, dict):
        return ""
    for key in ARG_KEYS:
        value = args.get(key)
        if isinstance(value, str) and value.strip():
            return " ".join(value.split())
    # Unknown tool: show the arguments rather than nothing, but compactly.
    try:
        return json.dumps(args, separators=(",", ":"))
    except (TypeError, ValueError):
        return ""


def flatten(text: Any) -> str:
    """Collapse a model's multi-line prose into something that fits one row."""
    if not isinstance(text, str):
        return ""
    return " ".join(text.split())


def result_text(result: Any) -> str:
    """Pull the human-readable part out of a tool result, for failure messages."""
    if isinstance(result, str):
        return flatten(result)
    if isinstance(result, dict):
        content = result.get("content")
        if isinstance(content, list):
            parts = [
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            joined = flatten(" ".join(parts))
            if joined:
                return joined
        return flatten(json.dumps(result, separators=(",", ":")))
    return ""


def elapsed(seconds: float) -> str:
    """`6m12s` reads faster than `372.4s` when you are scanning four workers."""
    total = int(seconds)
    if total < 60:
        return f"{total}s"
    if total < 3600:
        return f"{total // 60}m{total % 60:02d}s"
    return f"{total // 3600}h{(total % 3600) // 60:02d}m"


class Narrator:
    """Stateful because the interesting facts span events.

    A tool's duration is `tool_execution_end` minus `tool_execution_start`, and
    the running cost is a sum over turns — neither is on any single event.
    """

    def __init__(
        self,
        label: str,
        out: TextIO,
        alerts: TextIO | None = None,
        width: int = 200,
        heartbeat: int = 10,
        slow_tool: float = 20.0,
        show_thinking: bool = False,
        clock: Any = time.monotonic,
    ) -> None:
        self.label = label
        self.out = out
        self.alerts = alerts
        self.width = width
        self.heartbeat = heartbeat
        self.slow_tool = slow_tool
        self.show_thinking = show_thinking
        self.clock = clock
        self.started = clock()
        self.turn = 0
        self.tool_calls = 0
        self.cost = 0.0
        self.errors = 0
        self.finished = False
        self.pending: dict[str, tuple[str, float]] = {}

    def emit(self, symbol: str, text: str) -> None:
        stamp = f"{self.label} t{self.turn:<3} {elapsed(self.clock() - self.started):>6}"
        line = f"{stamp} {symbol} {text}"[: self.width]
        # One write, not print()'s two. Under pi-rpc.py the event reader and the
        # stderr reader share this stream, and a separate newline write lets one
        # thread's line land inside another's.
        self.out.write(line + "\n")
        self.out.flush()
        if self.alerts is not None and symbol in ALERT_SYMBOLS:
            # O_APPEND keeps concurrent workers from interleaving mid-line, so
            # every worker in a run can share one alerts file.
            self.alerts.write(line + "\n")
            self.alerts.flush()

    def feed(self, record: str) -> None:
        """Handle one line of pi's stdout. Never raises: visibility is best-effort."""
        text = record.strip()
        if not text:
            return
        try:
            event = json.loads(text)
        except ValueError:
            # Not JSON. With `2>&1` this is pi's own stderr — the settings-lock
            # warning, a provider error, a stack trace. Those used to vanish
            # into the log, and they are exactly what you want to see.
            self.emit("!", flatten(text))
            return
        if not isinstance(event, dict):
            return
        try:
            self.dispatch(event)
        except Exception as exc:  # noqa: BLE001 - a formatting bug must not kill the run
            self.emit("!", f"pi-narrate could not format a {event.get('type')} event: {exc}")

    def dispatch(self, event: dict[str, Any]) -> None:
        kind = event.get("type")
        if kind == "session":
            self.emit("○", f'session {str(event.get("id", ""))[:8]} in {event.get("cwd", "?")}')
        elif kind == "turn_start":
            self.turn += 1
        elif kind == "message_update":
            self.on_message_update(event.get("assistantMessageEvent") or {})
        elif kind == "tool_execution_start":
            self.on_tool_start(event)
        elif kind == "tool_execution_end":
            self.on_tool_end(event)
        elif kind == "turn_end":
            self.on_turn_end(event)
        elif kind in ("compaction_start", "compaction_end"):
            self.emit("⚠", kind.replace("_", " "))
        elif kind == "auto_retry_start":
            self.emit("⚠", f'retrying after an API error: {flatten(str(event.get("error", "")))}')
        elif kind == "extension_error":
            self.emit("!", f'extension error: {flatten(str(event.get("error", "")))}')
        elif kind == "agent_settled":
            # The real completion signal: pi's docs define it as "no automatic
            # retry, compaction retry, or queued continuation remains".
            self.finish()

    def finish(self) -> None:
        """The one completion line, however the run got here. Idempotent.

        Not driven by `agent_end`, which pi documents as *one low-level run*
        and which repeats across retries and compaction — narrating that as
        "done" reported completion several times in a retried run. Callers also
        invoke this when the stream ends, so a worker that dies before settling
        still gets exactly one closing line, and the alerts monitor still fires.
        """
        if self.finished:
            return
        self.finished = True
        self.emit(
            "■",
            f"done — {self.turn} turns, {self.tool_calls} tools, "
            f"{self.errors} failed, ${self.cost:.4f}",
        )

    def on_message_update(self, inner: dict[str, Any]) -> None:
        kind = inner.get("type")
        if kind == "text_end":
            said = flatten(inner.get("content"))
            if said:
                self.emit("»", said)
        elif kind == "thinking_end" and self.show_thinking:
            thought = flatten(inner.get("content"))
            if thought:
                self.emit("~", thought)

    def on_tool_start(self, event: dict[str, Any]) -> None:
        tool = str(event.get("toolName", "?"))
        self.tool_calls += 1
        call_id = event.get("toolCallId")
        if isinstance(call_id, str):
            self.pending[call_id] = (tool, self.clock())
        self.emit("▸", f"{tool} {brief(tool, event.get('args'))}".strip())

    def on_tool_end(self, event: dict[str, Any]) -> None:
        call_id = event.get("toolCallId")
        tool, started = self.pending.pop(call_id, (str(event.get("toolName", "?")), self.clock()))
        took = self.clock() - started
        if event.get("isError"):
            self.errors += 1
            # The guardrails extension refuses via an error result, so this is
            # also how a blocked `git push` surfaces — and it is worth an alert.
            self.emit("✗", f"{tool} FAILED after {elapsed(took)}: {result_text(event.get('result'))}")
        elif took >= self.slow_tool:
            # Only slow tools are worth a completion line; a 40-second suite run
            # finishing is news, a 20ms read is not.
            self.emit("✓", f"{tool} ok ({elapsed(took)})")

    def on_turn_end(self, event: dict[str, Any]) -> None:
        usage = (event.get("message") or {}).get("usage") or {}
        cost = (usage.get("cost") or {}).get("total")
        if isinstance(cost, (int, float)):
            self.cost += float(cost)
        if self.heartbeat > 0 and self.turn > 0 and self.turn % self.heartbeat == 0:
            self.emit("·", f"{self.turn} turns, {self.tool_calls} tools, ${self.cost:.4f}")


def records(stream: BinaryIO):
    """Split on LF only.

    pi's docs are explicit that the stream is strict JSONL with LF as the only
    delimiter, and that generic line readers are not protocol-compliant because
    they also split on U+2028/U+2029 — both of which are legal inside a JSON
    string, and both of which appear in real model output.
    """
    # `read1` returns whatever has arrived rather than waiting for a full
    # buffer, which is what makes the narration live. A plain `read(65536)`
    # would block until 64KB accumulated and stall the narration behind it, so
    # this requires read1 rather than silently falling back to it.
    read = getattr(stream, "read1", None)
    if read is None:  # pragma: no cover - both call sites pass a BufferedReader
        raise TypeError(f"{type(stream).__name__} has no read1; narration would not be live")

    buffer = b""
    # Where the last unsuccessful search reached. Without it, every 64KB chunk
    # rescans the whole buffer from zero, which is quadratic on exactly the
    # biggest event: `agent_end` carries every message in the session and runs
    # to megabytes on one line.
    searched = 0
    while True:
        chunk = read(65536)
        if not chunk:
            break
        buffer += chunk
        while True:
            index = buffer.find(b"\n", searched)
            if index < 0:
                searched = len(buffer)
                break
            yield buffer[:index]
            buffer = buffer[index + 1 :]
            searched = 0
    if buffer:
        yield buffer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Narrate a pi --mode json event stream in one line per event.",
    )
    parser.add_argument(
        "--label",
        default=os.environ.get("PI_LABEL", "worker"),
        help="Prefix identifying this worker (default: $PI_LABEL, else 'worker').",
    )
    parser.add_argument("--raw", help="Also write the untouched JSONL here.")
    parser.add_argument(
        "--alerts",
        help="Append alert-worthy lines here. Share one file across a run's workers.",
    )
    parser.add_argument("--width", type=int, default=200, help="Truncate lines to N chars.")
    parser.add_argument(
        "--heartbeat",
        type=int,
        default=10,
        help="Emit a turn/cost line every N turns; 0 disables.",
    )
    parser.add_argument(
        "--slow-tool",
        type=float,
        default=20.0,
        help="Report a tool's completion only if it took at least N seconds.",
    )
    parser.add_argument(
        "--thinking",
        action="store_true",
        help="Also narrate reasoning. Off by default: it is long and mostly restates the task.",
    )
    args = parser.parse_args(argv)

    raw = None
    alerts = None
    try:
        if args.raw:
            os.makedirs(os.path.dirname(os.path.abspath(args.raw)), exist_ok=True)
            # Append, not truncate: a re-run or a `--continue` feedback pass
            # points at the same path, and losing the first run's log is
            # exactly the outcome this tool exists to prevent.
            raw = open(args.raw, "ab")
        if args.alerts:
            os.makedirs(os.path.dirname(os.path.abspath(args.alerts)), exist_ok=True)
            alerts = open(args.alerts, "a", encoding="utf-8")

        narrator = Narrator(
            label=args.label,
            out=sys.stdout,
            alerts=alerts,
            width=args.width,
            heartbeat=args.heartbeat,
            slow_tool=args.slow_tool,
            show_thinking=args.thinking,
        )

        for record in records(sys.stdin.buffer):
            if raw is not None:
                # Write the raw record before formatting it. A bug in the
                # narrator must never cost us the log it was reading.
                raw.write(record + b"\n")
                raw.flush()
            narrator.feed(record.decode("utf-8", errors="replace"))
        # The stream ended. If pi never settled — it crashed, or was killed —
        # this is still the end of the run, and the alerts monitor is watching
        # for exactly one closing line per worker.
        narrator.finish()
    except KeyboardInterrupt:
        return 130
    except BrokenPipeError:
        return 0
    finally:
        for handle in (raw, alerts):
            if handle is not None:
                try:
                    handle.close()
                except OSError:
                    pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
