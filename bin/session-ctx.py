#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Print the context size of a Claude Code session, and exit 1 past a cap.

Every turn re-reads the whole context, so an orchestrator that grows to 370k
tokens costs several times one held under 150k. The size is input plus cache
read plus cache creation tokens on the last assistant message. Claude Code
streams a message as several transcript lines sharing one id; the last chunk
holds the final usage.

    session-ctx.py [transcript.jsonl] [--cap N]

With no path, reads the newest transcript for the current directory under
~/.claude/projects/. Prints OVER and exits 1 above the cap (default 150000).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
USAGE_KEYS = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")


def newest_transcript(cwd: Path) -> Path | None:
    """The most recently written transcript for a working directory."""
    folder = PROJECTS / re.sub(r"[^A-Za-z0-9]", "-", str(cwd))
    found = sorted(folder.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    return found[-1] if found else None


def context_tokens(transcript: Path) -> int | None:
    """Context size at the last assistant message, or None when it has none."""
    last: dict[str, int] = {}
    order: list[str] = []
    for line in transcript.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        message = event.get("message") if isinstance(event, dict) else None
        if event.get("type") != "assistant" or event.get("isSidechain") or not isinstance(message, dict):
            continue
        usage = message.get("usage")
        if not isinstance(usage, dict):
            continue
        key = str(message.get("id") or len(order))
        if key not in last:
            order.append(key)
        last[key] = sum(int(usage.get(k) or 0) for k in USAGE_KEYS)
    return last[order[-1]] if order else None


def short(tokens: int) -> str:
    """253000 as 253k."""
    return f"{round(tokens / 1000)}k"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("transcript", nargs="?", type=Path, help="default: newest for the current directory")
    p.add_argument("--cap", type=int, default=150000, help="tokens past which it prints OVER and exits 1")
    args = p.parse_args(argv)
    path = args.transcript or newest_transcript(Path.cwd())
    tokens = context_tokens(path) if path else None
    if tokens is None:
        print("session-ctx.py: no transcript with an assistant message found", file=sys.stderr)
        return 2
    over = tokens > args.cap
    print(f"{tokens} tokens (cap {args.cap})" + (" OVER" if over else ""))
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())
