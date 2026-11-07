#!/usr/bin/env python3
"""Block a commit, push or merge that rides on a test piped into another command. A Claude Code PreToolUse hook.

`./verify.sh | tail -1 && git push` pushes on a red gate: a pipeline's status is
its last command's, so `tail` decides. A CLAUDE.md rule against it lost twice
(gridkeep, 2026-11-07, main red twice), so this refuses the command instead.
It allows the pipe when `pipefail` is set earlier in the same command. Exit 2
blocks the call and shows stderr to Claude. Any error lets the command through.

Not covered: a test piped in one Bash call and the commit sent in the next.
"""

from __future__ import annotations

import json
import re
import sys

WRITE = re.compile(r"\bgit\b[^|;&\n]*\b(commit|push|merge)\b")
# A gate, then a lone pipe.
PIPED_GATE = re.compile(
    r"(verify\.sh|test\.sh|quick\.sh|land_check\.sh|run_tests\.sh|\bpytest\b|\bgo\s+test\b|\bcargo\s+test\b|\bnpm\s+(?:run\s+)?test\b|\bjust\s+test\b)"
    r"(?:(?!&&|;|\n).)*?(?<!\|)\|(?!\|)"
)


def piped_gate_before_write(command: str) -> bool:
    write = WRITE.search(command)
    if not write:
        return False
    before = command[: write.start()]
    if "pipefail" in before:
        return False
    return bool(PIPED_GATE.search(before))


def main() -> int:
    event = json.load(sys.stdin)
    command = event["tool_input"]["command"]
    if piped_gate_before_write(command):
        print(
            "Blocked: a test or gate is piped into another command before this git "
            "commit/push/merge, so the pipe's exit status (tail's, head's) decides, not "
            "the test's. Capture the result first, e.g. `./verify.sh > out 2>&1; rc=$?; "
            'tail -1 out; [ $rc -eq 0 ] && git push`, or add `set -o pipefail`.',
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # never block on the hook's own failure
        sys.exit(0)
