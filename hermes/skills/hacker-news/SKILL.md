---
name: hacker-news
description: Read a Hacker News thread with its comments. Use when given a news.ycombinator.com link or asked what HN said about something.
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

Run with the `terminal` tool:

```bash
fetch-thread.py "https://news.ycombinator.com/item?id=<id>"   # story and comment tree
```

To find a thread, web-search `site:news.ycombinator.com <topic>`, then read the
best match.
