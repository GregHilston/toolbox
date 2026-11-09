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

- A 403 or 429 is often only this host's IP being blocked. `fetch-thread.py` then
  reruns itself over ssh on dungeon, then FOB (`$FETCH_THREAD_RELAYS`), and says so
  on stderr. `reddit-search.py` does not: run it through `ssh dungeon '…'`.
- If `reddit-search.py` answers 403 everywhere (it did from moria and dungeon on
  2026-11-08), find threads with DeepSeek Search instead:
  `POST https://api.deepseek.com/v1/tools/search` with `{"query": "site:reddit.com <game> <topic>", "count": 8}`
  and `Authorization: Bearer $DEEPSEEK_API_KEY`. Drop the `?solution=…` tail from each
  result's URL, then read it with `fetch-thread.py`. Name the game or subreddit in the
  query: game-specific queries found relevant threads 6 of 6 times, generic design ones 0
  of 2. Results carry a summary but no page text, and DeepSeek Fetch answers 404 on Reddit.
  It costs $0.75 per 1,000 searches (nine cost about a cent), and the query leaves for
  DeepSeek, so never search anything private this way.
- Through the dungeon relay, `fetch-thread.py` returns the comments but the post body is
  rate-limited (429), and two reads back to back trip the limit: leave about a minute
  between threads (75 seconds worked 4 of 4). A DeepSeek Search summary holds the post
  body when the thread is indexed, but it missed 2 of 2 posts on 2026-11-08.
- If both commands break, `REDDIT_LIVE=1 python3 -m unittest test_fetch_reddit_live` in
  `toolbox/tests/` says what Reddit changed. pi's `reddit_*` tools use the old endpoints and
  are unreliable.
- Do not use `searxngr` to find Reddit threads: its egress IP is blocked by every engine
  that indexes Reddit deeply (DuckDuckGo and Startpage CAPTCHA, Brave rate-limits, Google
  and Mojeek return nothing). It still works for general web search (Bing and Yahoo answer;
  on 2026-10-18 it beat DeepSeek Search on dev queries, `home-lab/docs/llm-gateway.md`).
