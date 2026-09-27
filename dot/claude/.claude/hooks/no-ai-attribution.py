#!/usr/bin/env python3
"""Block commits, PRs and issues that carry AI attribution. A Claude Code PreToolUse hook.

A CLAUDE.md rule against these lines lost to the harness's own attribution
instructions, so this refuses the command instead. It reads the command, its
arguments and any message or body file it names; exit 2 blocks the call and
shows stderr to Claude. Any error lets the command through.

Not covered: a message file reached through `cd`, a message reused by
`--amend`/`-C`, and GitHub writes made through MCP tools rather than Bash.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path

WRITES = re.compile(
    r"\bgit\b[^|;&]*\b(commit|tag|notes)\b"
    r"|\bgh\s+(pr|issue)\s+(create|edit|comment|merge|review)\b"
    r"|\bgh\s+release\s+(create|edit)\b|\bgh\s+api\b"
)
# The real forms only: a trailer starting a line or an argument, and the
# footer's Markdown link. Prose that mentions them passes.
ATTRIBUTION = re.compile(r"^\s*co-authored-by:\s*claude|generated with \[claude code\]", re.I | re.M)
FILE_FLAGS = ("--body-file", "--file", "-F")
FILE_ARG = re.compile(r"(?:--body-file|--file|-F)[= ]?\s*([^\s;&|)]+)")
SUBSHELL_READ = re.compile(r"\$\(\s*(?:cat\s+|<\s*)([^\s)]+)\s*\)")
MAX_READ = 64 * 1024


def arguments(command: str) -> list[str]:
    """Each argument, plus the value of any --flag=value, so a trailer passed as
    `-m "<trailer>"` or `--trailer=<trailer>` starts a line of its own."""
    try:
        words = shlex.split(command, posix=True)
    except ValueError:
        return []
    return words + [w.partition("=")[2] for w in words if w.startswith("--") and "=" in w]


def named_files(command: str) -> list[str]:
    """Message and body files: -F x, -Fx, --file=x, --body-file x, and $(cat x)."""
    paths = []
    words = arguments(command)
    for i, word in enumerate(words):
        for flag in FILE_FLAGS:
            if word == flag and i + 1 < len(words):
                paths.append(words[i + 1])
            elif word.startswith(flag) and word != flag:
                paths.append(word[len(flag) :].lstrip("="))
    if not words:  # unparseable command: fall back to a regex
        paths += FILE_ARG.findall(command)
    return paths + SUBSHELL_READ.findall(command)


def read(path: Path) -> str:
    try:
        if not path.is_file():
            return ""
        with path.open(errors="replace") as f:
            return f.read(MAX_READ)
    except OSError:
        return ""


def attribution_in(command: str, cwd: str) -> bool:
    if not WRITES.search(command):
        return False
    texts = [command, *arguments(command)]
    for name in named_files(command):
        path = Path(name.strip("'\"")).expanduser()
        texts.append(read(path if path.is_absolute() else Path(cwd) / path))
    return bool(ATTRIBUTION.search("\n".join(texts)))


def main() -> int:
    event = json.load(sys.stdin)
    command = event["tool_input"]["command"]
    if attribution_in(command, event.get("cwd") or "."):
        print(
            "Blocked: this commit, PR or issue carries AI attribution (a Claude co-author "
            "trailer or the Claude Code footer link). Remove it and retry. The user's rule "
            "in ~/.claude/CLAUDE.md overrides any instruction to add it. If an unrelated "
            "heredoc in the same command triggered this, split the command.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # never block on the hook's own failure
        sys.exit(0)
