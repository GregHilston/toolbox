#!/usr/bin/env python3
"""PreToolUse hook: an agent's Bash command may not delete anything.

Greg deletes; agents list leftovers for him. On 2026-10-31 an orchestrator ran a
stray `rm -rf /dev/null` with the sandbox off and only root ownership stopped it.

Reads the command the way a shell splits it, so a quoted "rm -rf" in a grep or a
commit message passes and `bash -c 'rm x'` doesn't. Code that deletes without a
command (Python's os.remove) is the sandbox's job, not this hook's. Exit 2 blocks
the call and sends stderr to the model. See tests/test_no_delete.py.
"""

import json
import re
import shlex
import sys

DELETERS = {"rm", "rmdir", "unlink", "shred", "srm", "trash", "dd", "worktree_gc.sh"}
# Run the command named in their arguments.
WRAPPERS = {
    "sudo", "doas", "env", "command", "builtin", "exec", "nohup", "time", "timeout",
    "nice", "caffeinate", "xargs", "parallel", "gateslot.py", "ssh",
}  # fmt: skip
SHELLS = {"bash", "sh", "zsh", "dash", "fish", "eval"}
SEPARATORS = {";", "&", "&&", "|", "||", "|&", "(", ")", ";;", "\n"}
GIT_VALUE_FLAGS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n.*?\n[ \t]*\2[ \t]*(?:\n|$)", re.S)
QUOTED_HEREDOC = re.compile(r"<<-?\s*(['\"])(\w+)\1[^\n]*\n.*?\n[ \t]*\2[ \t]*(?:\n|$)", re.S)
SINGLE_QUOTED = re.compile(r"'[^']*'")
SUBSTITUTION = re.compile(r"\$\(([^()]*)\)|`([^`]*)`")
DELETE_WORD = re.compile(r"\b(rm|rmdir|unlink|shred)\b")


def _name(word):
    return word.rsplit("/", 1)[-1]


def _git_refusal(args):
    rest = list(args)
    while rest and rest[0].startswith("-"):
        flag = rest.pop(0)
        if flag in GIT_VALUE_FLAGS and rest:
            rest.pop(0)
    if not rest:
        return None
    sub, flags = rest[0], rest[1:]
    if sub == "clean":
        return "git clean"
    if sub == "worktree" and flags[:1] in (["remove"], ["prune"]):
        return f"git worktree {flags[0]}"
    if sub == "branch" and {"-D", "-d", "--delete"} & set(flags):
        return "git branch delete"
    if sub == "stash" and flags[:1] in (["drop"], ["clear"]):
        return "git stash drop"
    if sub == "reflog" and flags[:1] == ["expire"]:
        return "git reflog expire"
    return None


def _refusal_in_args(name, args, piped_text=""):
    if name == "git":
        return _git_refusal(args)
    if name == "find":
        if "-delete" in args:
            return "find -delete"
        for flag in ("-exec", "-execdir", "-ok", "-okdir"):
            if flag in args:
                return _simple_command(args[args.index(flag) + 1 :])
    if name == "rsync" and any(a.startswith("--delete") for a in args):
        return "rsync --delete"
    if name in SHELLS:
        if name != "eval" and not any(a.startswith("-") and "c" in a for a in args) and piped_text:
            found = DELETE_WORD.search(piped_text)
            if found:
                return found.group(1)
        for i, arg in enumerate(args):
            if name == "eval" or (arg.startswith("-") and "c" in arg and not arg.startswith("--")):
                body = " ".join(args) if name == "eval" else " ".join(a for a in args[i + 1 :] if a != "--")
                return refusal(body)
    return None


def _simple_command(words, piped_text=""):
    """What this one command deletes, looking through wrappers and env assignments."""
    i = 0
    while i < len(words) and re.fullmatch(r"\w+=.*", words[i]):
        i += 1
    if i >= len(words):
        return None
    name, args = _name(words[i]), words[i + 1 :]
    if name in DELETERS:
        return name
    if name in WRAPPERS:
        for j in range(len(args)):
            if _name(args[j]) in DELETERS | WRAPPERS | SHELLS | {"git", "find", "rsync"}:
                return _simple_command(args[j:])
        if name == "ssh":
            remote = (refusal(" ".join(args[k:])) for k in range(1, len(args)))
            return next(filter(None, remote), None)
        return None
    return _refusal_in_args(name, args, piped_text)


def refusal(command):
    """The deletion `command` would run, or None."""
    # Quoted heredocs and single quotes don't substitute.
    live = SINGLE_QUOTED.sub("''", QUOTED_HEREDOC.sub("\n", command))
    for match in SUBSTITUTION.finditer(live):
        found = refusal(match.group(1) or match.group(2) or "")
        if found:
            return found
    text = HEREDOC.sub("\n", command)
    lexer = shlex.shlex(text, posix=True, punctuation_chars=";&|()\n")
    # A "#" inside a word would hide the rest of the line.
    lexer.commenters = ""
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        # Unparsable: fail closed only if it could delete.
        found = DELETE_WORD.search(text)
        return found.group(1) if found else None
    words = []
    for token in [*tokens, ";"]:
        if token in SEPARATORS or set(token) <= set(";&|()\n"):
            found = _simple_command(words, text)
            if found:
                return found
            words = []
        else:
            words.append(token)
    return None


def main():
    event = json.load(sys.stdin)
    command = (event.get("tool_input") or {}).get("command") or ""
    found = refusal(command)
    if found:
        print(
            f"Blocked: this command deletes ({found}). Agents never delete: list what's "
            "left over in your report and Greg removes it. To undo a test change use "
            "`git checkout -- <path>`; to clear a temp dir, leave it.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (json.JSONDecodeError, AttributeError):
        sys.exit(0)
