---
name: reddit
description: Search Reddit and read threads with their comments, no login needed. Use for anything about what people on Reddit say, recommend or report.
version: 1.0.0
author: Greg Hilston
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [reddit, research, web]
    requires_toolsets: [terminal]
---

# Reddit

Two commands, already on `PATH`. Run them with the `terminal` tool exactly as
shown: no `python3` in front and no directory. They are not tools themselves.

```bash
reddit-search.py "<query>"                   # threads: title, votes, comments, link
reddit-search.py "<query>" -r <subreddit>    # one subreddit (repeat -r for more)
reddit-search.py "<query>" -s top -t year    # sort: relevance|hot|top|new|comments
fetch-thread.py "<thread url>"               # the post and its top 25 comments
fetch-thread.py "<thread url>" -n 50         # more comments; long output may be cut
```

Search first, then read the two or three threads whose titles actually fit:
Reddit's search is fuzzy and returns posts even when nothing matches.

Do not use web search, Reddit's `.json` API or old.reddit.com for Reddit. They are
blocked or login-walled.
