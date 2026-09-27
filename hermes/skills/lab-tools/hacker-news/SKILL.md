---
name: hacker-news
description: Search Hacker News and read threads with their comments, no key needed. Use when given a news.ycombinator.com link or asked what HN said about something.
version: 1.0.0
author: Greg Hilston
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [hacker-news, research, web]
    requires_toolsets: [terminal]
---

# Hacker News

Two commands, already on `PATH`. Run them with the `terminal` tool exactly as
shown: no `python3` in front and no directory. They are not tools themselves.

```bash
hn-search.py "<query>"                                          # stories: points, comments, thread link
hn-search.py "<query>" -s date                                  # newest first
fetch-thread.py "https://news.ycombinator.com/item?id=<id>"     # story and comment tree
```

Search first, then read the one or two threads whose titles fit.
