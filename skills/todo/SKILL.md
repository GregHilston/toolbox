---
name: todo
description: Add a task Greg must do himself to his todo list in the notes vault, then commit and push it. Use for /todo, or when asked to add a todo, a task or a reminder for something he has to do. Not for waiting on someone else (watch) or someday ideas (later).
argument-hint: <task text> [by <date>]
license: MIT
---

# Todo

One command, already on `PATH`. Run it in your shell (the `terminal` tool in
Hermes, Bash in Claude Code, `bash` in pi) exactly as shown: no `python3` in
front and no directory. It is not a tool itself.

```bash
notes-task.py todo "<task text>"
notes-task.py todo "<task text>" --due YYYY-MM-DD
```

The task text is whatever follows `/todo`, or the task in Greg's request.

- **Keep his wording.** Fix only spacing and obvious typos; never reword.
- **Drop any `#todo`, `#watch` or `#later`** from the text: the command adds
  the tag and refuses text that already has one.
- **Pass `--due` only when he gave a date.** Turn "friday" or "next week" into
  YYYY-MM-DD from today's date, and take the date words out of the text.
- **Quote the text** so the shell keeps it whole.

The command prints the line it added, then `pushed` or why it did not push.
Reply in one short sentence with that line, and say so if it did not push.
Exit 2 means bad input and nothing written: fix the text or date and run again.

Do not edit `quick-todo.md` or run `git` yourself: the command does both.
