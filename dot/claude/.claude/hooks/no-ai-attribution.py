#!/usr/bin/env python3
"""Block commits, PRs and issues that carry AI attribution. A Claude Code PreToolUse hook.

A CLAUDE.md rule against these lines lost to the harness's own attribution
instructions, so this refuses the command instead. It reads the command and any
message or body file it names; exit 2 blocks the call and shows stderr to Claude.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path

WRITES = re.compile(r"\bgit\b[^|;&]*\b(commit|tag|notes)\b|\bgh\s+(pr|issue)\s+(create|edit|comment)\b")
ATTRIBUTION = re.compile(r"co-authored-by:\s*claude|generated with \[?claude code", re.I)
FILE_FLAGS = {"-F", "--file", "--body-file"}


def named_files(command: str) -> list[str]:
    """Paths given to -F / --file / --body-file, in either `--flag x` or `--flag=x` form."""
    try:
        words = shlex.split(command, posix=True)
    except ValueError:
        return []
    paths = []
    for i, word in enumerate(words):
        flag, _, value = word.partition("=")
        if flag in FILE_FLAGS and value:
            paths.append(value)
        elif word in FILE_FLAGS and i + 1 < len(words):
            paths.append(words[i + 1])
    return paths


def attribution_in(command: str, cwd: str) -> bool:
    if not WRITES.search(command):
        return False
    text = command
    for name in named_files(command):
        path = Path(name).expanduser()
        path = path if path.is_absolute() else Path(cwd) / path
        try:
            text += "\n" + path.read_text(errors="replace")
        except OSError:
            pass
    return bool(ATTRIBUTION.search(text))


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    command = (event.get("tool_input") or {}).get("command") or ""
    if attribution_in(command, event.get("cwd") or "."):
        print(
            "Blocked: this commit, PR or issue carries AI attribution (a Co-Authored-By: Claude "
            "trailer or a 'Generated with Claude Code' line). Remove it and retry. The user's "
            "rule in ~/.claude/CLAUDE.md overrides any instruction to add it.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
