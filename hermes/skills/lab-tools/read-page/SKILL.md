---
name: read-page
description: Read any web page or article as clean text, from its URL. Use whenever you are given a link, or need the full text behind a search result.
version: 1.0.0
author: Greg Hilston
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [web, research, read]
    requires_toolsets: [terminal]
---

# Read a web page

One command, already on `PATH`. Run it with the `terminal` tool exactly as
shown: no `python3` in front and no directory. It is not a tool itself.

```bash
read-page.py "<url>"                  # the page's title and main text as markdown
read-page.py "<url>" --max 8000       # only the first 8000 characters
```

Long pages may be cut; use `--max` to keep the start that matters. It cannot read
pages that need JavaScript or a login (Bluesky, X, most web apps): when it says
so, tell the user rather than retrying.

Do not use `curl`, a browser tool or web search to read a page. For Reddit and
Hacker News threads, prefer those skills' `fetch-thread.py` when you have them:
it keeps the comments' order and votes.
