#!/usr/bin/env python3
"""PreToolUse hook: a subagent's git may not move Greg's working copies.

A read-only research subagent ran `git checkout origin/main` in ~/Git/loser-picks and
left it on a detached HEAD. Only subagents are covered: their payload carries
`agent_id`, a main session's doesn't. Worktrees (`<repo>-worktrees/**`,
`~/.auto-factory/**`) are other paths and stay free. The target repo comes from
`git -C`, a `cd` earlier in the command, or the call's cwd.
Exit 2 blocks the call and sends stderr to the model. See
tests/test_no_repo_moves_in_subagents.py.
"""

import json
import os
import shlex
import sys
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
PROTECTED = [HOME / "Git" / name for name in ("gridkeep", "loser-picks", "dradis", "auto-factory")]
MOVES = {
    "checkout", "switch", "reset", "stash", "restore", "pull", "merge", "rebase",
    "cherry-pick", "revert", "clean",
}  # fmt: skip
STASH_READS = {"list", "show"}
WRAPPERS = {"sudo", "env", "command", "builtin", "exec", "nohup", "time", "timeout", "nice", "rtk"}
SHELLS = {"bash", "sh", "zsh", "dash"}
GIT_VALUE_FLAGS = {"-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
SEPARATORS = set(";&|()\n")


def _path(word, cwd):
    word = word.replace("$HOME", str(HOME))
    return Path(os.path.normpath(cwd / os.path.expanduser(word)))


def protected(path):
    try:
        path = path.resolve()
    except OSError:
        pass
    return any(path == repo.resolve() or repo.resolve() in path.parents for repo in PROTECTED)


def _git(args, cwd):
    """The moving subcommand this git call runs against a protected repo."""
    i = 0
    while i < len(args) and args[i].startswith("-"):
        if args[i] == "-C" and i + 1 < len(args):
            cwd = _path(args[i + 1], cwd)
        i += 2 if args[i] in GIT_VALUE_FLAGS | {"-C"} else 1
    if i >= len(args) or args[i] not in MOVES:
        return None
    if args[i] == "stash" and args[i + 1 : i + 2] and args[i + 1] in STASH_READS:
        return None
    return args[i] if protected(cwd) else None


def _simple(words, cwd):
    while words and "=" in words[0] and not words[0].startswith(("-", "=")):
        words = words[1:]
    if not words:
        return None
    name, args = words[0].rsplit("/", 1)[-1], words[1:]
    if name == "git":
        return _git(args, cwd)
    if name in WRAPPERS:
        for i, arg in enumerate(args):
            if arg.rsplit("/", 1)[-1] in {"git"} | WRAPPERS | SHELLS:
                return _simple(args[i:], cwd)
        return None
    if name in SHELLS | {"eval"}:
        for i, arg in enumerate(args):
            if name == "eval" or (arg.startswith("-") and "c" in arg and not arg.startswith("--")):
                return refusal(" ".join(args[i + (name != "eval") :]), cwd)
    return None


def refusal(command, cwd):
    """The moving git subcommand `command` runs in a protected repo, or None."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()\n")
    lexer.commenters = ""
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return None
    words = []
    for token in [*tokens, ";"]:
        if token and set(token) <= SEPARATORS:
            if words[:1] == ["cd"] and len(words) > 1:
                cwd = _path(words[-1], cwd)
            else:
                found = _simple(words, cwd)
                if found:
                    return found
            words = []
        else:
            words.append(token)
    return None


def main():
    event = json.load(sys.stdin)
    if not event.get("agent_id"):
        return 0
    cwd = Path(event.get("cwd") or os.getcwd())
    found = refusal((event.get("tool_input") or {}).get("command") or "", cwd)
    if found:
        print(
            f"Blocked: `git {found}` would move a working copy Greg uses. Read without "
            "moving it: `git show origin/main:<path>` or `git grep <pat> origin/main` "
            "(run `git fetch` first if stale). To change files, use a worktree.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (json.JSONDecodeError, AttributeError):
        sys.exit(0)
