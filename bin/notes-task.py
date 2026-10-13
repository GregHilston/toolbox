#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Capture a task into the notes vault's quick-todo.md, then commit and push it.

    notes-task.py todo "call the plumber"
    notes-task.py watch "reply from Dausen" --due 2026-10-20
    notes-task.py later "fix the front light"

Appends `- [ ] <text> #<list>` (and ` 📅 <date>`) to the end of the matching
`## Todo` / `## Watch` / `## Later` section, which the Obsidian Tasks plugin
lists in tasks.md. Vault: $NOTES_DIR, else /notes (Hermes), else ~/Git/notes.
Inside Hermes, notes-sync.sh ($NOTES_SYNC overrides its path) does the git
work; elsewhere this script does.
A failed push keeps the local commit and exits 0: the task is saved.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

LISTS = ("todo", "watch", "later")
NOTE = "quick-todo.md"
HERMES_SYNC = "/opt/data/scripts/notes-sync.sh"
TAG = re.compile(r"#(todo|watch|later)\b", re.IGNORECASE)


def vault() -> Path:
    if os.environ.get("NOTES_DIR"):
        return Path(os.environ["NOTES_DIR"])
    if Path("/notes").is_dir():
        return Path("/notes")
    return Path.home() / "Git" / "notes"


def task_line(kind: str, text: str, due: str | None) -> str:
    text = " ".join(text.split())
    if not text:
        raise ValueError("the task text is empty")
    if TAG.search(text):
        raise ValueError("leave out #todo/#watch/#later: the command adds the one tag")
    line = f"- [ ] {text} #{kind}"
    if due is not None:
        try:
            ok = date.fromisoformat(due).isoformat() == due
        except ValueError:
            ok = False
        if not ok:
            raise ValueError(f"bad --due {due!r}: want YYYY-MM-DD")
        # Tasks reads fields from the end.
        line += f" 📅 {due}"
    return line


def insert(body: str, kind: str, line: str) -> str:
    """Put the line after the last one in its section, else at the end."""
    lines = body.splitlines()
    heading = re.compile(rf"^##\s+{kind}\b", re.IGNORECASE)
    start = next((i for i, l in enumerate(lines) if heading.match(l)), None)
    end = len(lines)
    if start is not None:
        end = next((i for i in range(start + 1, len(lines)) if re.match(r"^#{1,2}\s", lines[i])), end)
    while end > 0 and not lines[end - 1].strip():
        end -= 1
    lines.insert(end, line)
    return "\n".join(lines) + "\n"


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)


def failure(proc: subprocess.CompletedProcess) -> str:
    out = (proc.stderr or proc.stdout).strip()
    return out.splitlines()[-1] if out else f"exit {proc.returncode}"


def sync(root: Path, message: str, hermes_sync: Path) -> str:
    """Commit and push the note; return a line saying how far it got.

    Commit, rebase, push: notes-sync.sh's order. The vault's merge=union
    keeps the rebase from stopping on a text conflict.
    """
    if hermes_sync.exists():
        proc = subprocess.run([str(hermes_sync), "push", message], capture_output=True, text=True,
                              env={**os.environ, "NOTES_VAULT": str(root)})
        return "pushed" if proc.returncode == 0 else f"saved but not pushed: {failure(proc)}"
    commit = git(root, "commit", "-q", "-m", message, "--", NOTE)
    if commit.returncode != 0:
        return f"saved but not committed: {failure(commit)}"
    pull = git(root, "pull", "-q", "--rebase", "--autostash")
    if pull.returncode != 0:
        git(root, "rebase", "--abort")
        return f"committed locally, not pushed (pull failed): {failure(pull)}"
    push = git(root, "push", "-q")
    return "pushed" if push.returncode == 0 else f"committed locally, not pushed: {failure(push)}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture a #todo, #watch or #later task into quick-todo.md.")
    parser.add_argument("list", choices=LISTS)
    parser.add_argument("text", nargs="+", help="the task, in plain words")
    parser.add_argument("--due", metavar="YYYY-MM-DD")
    args = parser.parse_args(argv)

    try:
        line = task_line(args.list, " ".join(args.text), args.due)
    except ValueError as err:
        print(f"notes-task: {err}", file=sys.stderr)
        return 2
    root = vault()
    note = root / NOTE
    try:
        note.write_text(insert(note.read_text(encoding="utf-8"), args.list, line), encoding="utf-8")
    except OSError as err:
        print(f"notes-task: cannot write {note}: {err}", file=sys.stderr)
        return 1
    print(f"added to {NOTE}: {line}")
    summary = " ".join(args.text)
    print(sync(root, f"docs(tasks): add #{args.list} {summary[:60]}", Path(os.environ.get("NOTES_SYNC", HERMES_SYNC))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
