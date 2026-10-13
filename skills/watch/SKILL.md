---
name: watch
description: Add a watch-list task to Greg's notes vault, for something he is waiting on someone else to do (a reply, a quote, a delivery, a callback). Use for /watch, or when asked to note that he is waiting on someone. Not for his own tasks (todo) or someday ideas (later).
argument-hint: "<what you are waiting on> [by <date>]"
license: MIT
---

# Watch

One command, already on `PATH`. Run it in your shell (the `terminal` tool in
Hermes, Bash in Claude Code, `bash` in pi) exactly as shown: no `python3` in
front and no directory. It is not a tool itself.

```bash
notes-task.py watch "<text>"                     # waiting on someone, no date
notes-task.py watch "<text>" --due YYYY-MM-DD    # only when Greg gave a date
```

The text is whatever follows `/watch`, or what Greg asked for in plain words.

- **Keep his wording.** Fix only obvious typos and stray spacing; never reword.
- **Drop any `#todo`, `#watch` or `#later`** in the text: the command adds the tag
  and refuses a line that already has one.
- **Pass `--due` only if he named a date.** Turn "next friday" or "the 20th" into
  YYYY-MM-DD from today's date; leave a date-free request without one.

The command appends the task to `quick-todo.md` in the vault, then commits and
pushes. It prints the added line, then `pushed` or why it did not. Reply in one
short sentence with that line, and add the second line only if it is not `pushed`.
Exit 2 means bad input and nothing was written: fix the text or date and run again.

Do not edit `quick-todo.md` by hand or run `git` yourself: the command does both.
