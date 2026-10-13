---
name: later
description: Add a someday task to Greg's later list in the notes vault, no pressure and no one waiting. Use for /later, or when Greg asks to note something to do someday or eventually. Not for things he must do (todo) or is waiting on someone else for (watch).
argument-hint: "<task> [by <date>]"
license: MIT
---

# Later

One command, already on `PATH`. Run it in your shell (the `terminal` tool in
Hermes, Bash in Claude Code, `bash` in pi) exactly as shown: no `python3` in
front and no directory. It is not a tool itself.

```bash
notes-task.py later "<task>"                    # append to quick-todo.md, commit and push
notes-task.py later "<task>" --due YYYY-MM-DD   # only when Greg gave a date
```

The task is the text after the slash command, or what Greg asked for in plain
words. Keep his wording: fix only typos and stray spaces. Drop any `#todo`,
`#watch` or `#later` tag in it, since the command adds the one tag and refuses
text that already has one. Turn a date he gave ("by next friday") into
YYYY-MM-DD from today's date and pass it as `--due`; never invent one.

The command prints the added line, then `pushed` or why not. Tell Greg the line
in one short sentence, plus the reason if it did not push. Exit 2 means bad
input and nothing was written: fix it and run again.

Do not edit `quick-todo.md` or any note by hand, and do not run git yourself:
the command does both.
