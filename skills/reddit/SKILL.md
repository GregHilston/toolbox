---
name: reddit
description: Search Reddit and read threads with their comments, no login needed. Use for anything about what people on Reddit say, recommend or report.
license: MIT
---

# Reddit

Two commands, already on `PATH`. Run them in your shell (the `terminal` tool in
Hermes, Bash in Claude Code, `bash` in pi) exactly as shown: no `python3` in
front and no directory. They are not tools themselves.

```bash
reddit-search.py "<query>"                   # threads: title, votes, comments, link
reddit-search.py "<query>" -r <subreddit>    # one subreddit (repeat -r for more)
reddit-search.py "<query>" -s top -t year    # sort: relevance|hot|top|new|comments
fetch-thread.py "<thread url>"               # the post and its top 25 comments
fetch-thread.py "<thread url>" -n 50         # more comments; long output may be cut
# fetch-thread.py also reads Hacker News thread URLs; add --format json for JSON
```

Search first, then read the two or three threads whose titles actually fit:
Reddit's search is fuzzy and returns posts even when nothing matches.

Do not use web search, Reddit's `.json` API or old.reddit.com for Reddit. They are
blocked or login-walled.

## When it fails

- A 403 on moria is often only moria's IP being blocked. Run the same command through
  `ssh dungeon '…'` before debugging.
- If both commands break, `REDDIT_LIVE=1 python3 -m unittest test_fetch_reddit_live` in
  `toolbox/tests/` says what Reddit changed. pi's `reddit_*` tools use the old endpoints and
  are unreliable.
- Do not use `searxngr` to find Reddit threads: its egress IP is blocked by every engine
  that indexes Reddit deeply (DuckDuckGo and Startpage CAPTCHA, Brave rate-limits, Google
  and Mojeek return nothing). It still works for general web search (Bing and Yahoo answer;
  on 2026-10-18 it beat DeepSeek Search on dev queries, `home-lab/docs/llm-gateway.md`).
