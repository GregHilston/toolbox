#!/usr/bin/env python3
"""Block `>>` that would create a new file under notes/llm. A Claude Code PreToolUse hook.

A no-op `cat >> llm/commander-log-<date>-tmp` leaves an empty stray file, and the
no-delete hook stops agents removing it (dradis #91, five times). Appending to
an existing file stays allowed. Exit 2 blocks the call. Any error lets it through.

Not covered: a `cd` earlier in the command, which moves what a relative target means.
"""

from __future__ import annotations

import json
import os
import re
import sys

LLM_DIR = os.path.expanduser("~/Git/notes/llm")
# `>>` then one quoted or bare word; `>>&` and `&>>` are not matched.
APPEND = re.compile(r"(?<![>&])>>\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s;&|<>()\"']+))")


def new_file_under_llm(command: str, cwd: str) -> bool:
    for m in APPEND.finditer(command):
        target = next(g for g in m.groups() if g is not None)
        target = target.replace("$HOME", "~", 1) if target.startswith("$HOME") else target
        if "$" in target or "`" in target:
            continue
        path = os.path.normpath(os.path.join(cwd, os.path.expanduser(target)))
        if path.startswith(LLM_DIR + os.sep) and not os.path.exists(path):
            return True
    return False


def main() -> int:
    event = json.load(sys.stdin)
    command = event["tool_input"]["command"]
    cwd = event.get("cwd") or os.getcwd()
    if new_file_under_llm(command, cwd):
        print(
            "Blocked: >> would create a new file under notes/llm. Append only to an "
            "existing log; write new notes with the Write tool.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # never block on the hook's own failure
        sys.exit(0)
