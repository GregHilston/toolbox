---
name: hacker-news
description: Search Hacker News and read threads with their comments, no key needed. Use when given a news.ycombinator.com link or asked what HN said about something.
license: MIT
---

# Hacker News

Two commands, already on `PATH`. Run them in your shell (the `terminal` tool in
Hermes, Bash in Claude Code, `bash` in pi) exactly as shown: no `python3` in
front and no directory. They are not tools themselves.

```bash
hn-search.py "<query>"                                          # stories: points, comments, thread link
hn-search.py "<query>" -s date                                  # newest first
fetch-thread.py "https://news.ycombinator.com/item?id=<id>"     # story and comment tree
```

Search first, then read the one or two threads whose titles fit.
