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

If an HN page answers with just "Sorry", the HTML site has flagged this IP
as a crawler; the block lifts on its own after a while. `fetch-thread.py`
reads the Firebase API instead, which is not blocked, so use it rather than
`read-page.py`, `curl` or a browser for any `news.ycombinator.com` link.
