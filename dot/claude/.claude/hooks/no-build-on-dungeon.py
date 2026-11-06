#!/usr/bin/env python3
"""PreToolUse hook: on dungeon, an agent's Bash command may not build or test.

dungeon is the home lab and runs services that must not stall; moria builds. On
2026-11-06 a session that took itself for moria ran `just validate`, `nix build` and
`nix flake check` on dungeon all afternoon. A command sent to moria with `ssh` passes.

Reads the command the way a shell splits it, like no-delete.py, so a quoted
"nix build" in a commit message passes and `bash -c 'nix build'` doesn't. The git
hooks' own `nix flake check` on push runs inside git, out of this hook's sight.
Exit 2 blocks the call and sends stderr to the model. See
tests/test_no_build_on_dungeon.py.
"""

import json
import re
import shlex
import socket
import sys

HOST = "dungeon"
BUILDERS = {"nix-build", "nix-shell", "nom", "nh", "nixos-rebuild", "darwin-rebuild"}
NIX_BUILDS = {"build", "develop"}
JUST_RECIPES = {"validate", "diff", "test", "ft", "dt", "fr", "dr", "fu"}
WRAPPERS = {
    "sudo", "env", "command", "builtin", "exec", "nohup", "time", "timeout", "nice",
    "caffeinate", "xargs", "gateslot.py",
}  # fmt: skip
SHELLS = {"bash", "sh", "zsh", "eval"}
SEPARATORS = set(";&|()\n")


def _name(word):
    return word.rsplit("/", 1)[-1]


def _simple(words):
    """The build this one command runs, looking through wrappers."""
    while words and re.fullmatch(r"\w+=.*", words[0]):
        words = words[1:]
    if not words:
        return None
    name, args = _name(words[0]), words[1:]
    if name == "ssh":
        return None
    if name in WRAPPERS:
        for i, arg in enumerate(args):
            if not arg.startswith("-") and not re.fullmatch(r"[\d.]+[smhd]?", arg):
                return _simple(args[i:])
        return None
    if name in SHELLS:
        if name == "eval":
            return refusal(" ".join(args))
        for i, arg in enumerate(args):
            if arg.startswith("-") and "c" in arg and not arg.startswith("--"):
                return refusal(" ".join(a for a in args[i + 1 :] if a != "--"))
        return None
    if name in BUILDERS:
        return name
    plain = [a for a in args if not a.startswith("-")]
    if name == "nix" and plain:
        # A flag's value can precede the subcommand.
        for word in plain[:2]:
            if word in NIX_BUILDS:
                return f"nix {word}"
        if "flake" in plain[:2] and "check" in plain[:3]:
            return "nix flake check"
    if name == "just" and plain and plain[0] in JUST_RECIPES:
        return f"just {plain[0]}"
    return None


def refusal(command):
    """The build `command` would run, or None."""
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
        if set(token) <= SEPARATORS:
            found = _simple(words)
            if found:
                return found
            words = []
        else:
            words.append(token)
    return None


def main():
    if socket.gethostname().split(".")[0].lower() != HOST:
        return 0
    event = json.load(sys.stdin)
    found = refusal((event.get("tool_input") or {}).get("command") or "")
    if found:
        print(
            f"Blocked: this is dungeon, and `{found}` builds or tests. dungeon runs the "
            "home lab's services; build on moria instead: `ssh moria '<command>'` against "
            "a fresh clone of the branch.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (json.JSONDecodeError, AttributeError):
        sys.exit(0)
