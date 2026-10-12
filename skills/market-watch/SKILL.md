---
name: market-watch
description: List, add or remove the Craigslist search terms watched near Sheldon, VT, which feed the market bot's hourly Telegram alerts and the morning digest. Use when Greg asks what Craigslist is being watched for, or to watch or stop watching for something.
license: MIT
---

# Market watch

One command, already on `PATH`. Run it in your shell (the `terminal` tool in
Hermes, Bash in Claude Code, `bash` in pi) exactly as shown: no `bash` in
front and no directory.

```bash
market-watch.sh list                  # every term, one per line
market-watch.sh add delta pro         # start watching; prints what it stored
market-watch.sh remove delta pro      # stop watching
```

Terms match listing titles. Case, spacing, hyphens and a plural do not matter
("ecoflow" finds Eco flow, Eco-Flow and EcoFlows), but a different name or a
typo does, so add each name a product goes by. Terms under two letters are
refused.

What counts as a deal (price, distance, condition) is judged by a model
afterwards, not by the term. Do not edit the list's file by hand or through
home-lab's config: this command is the way in.
