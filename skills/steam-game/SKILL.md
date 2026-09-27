---
name: steam-game
description: A Steam game's price and discount, review score, Steam Deck rating, and Linux/ProtonDB support, no key needed. Use for any question about a PC game on Steam.
license: MIT
---

# Steam games

One command, already on `PATH`. Run it in your shell (the `terminal` tool in
Hermes, Bash in Claude Code, `bash` in pi) exactly as shown: no `python3` in
front and no directory. It is not a tool itself.

```bash
steam-game.py "<game name>"                   # the best match, and other matches
steam-game.py <app id>                        # an exact game, e.g. 1145360
steam-game.py "<store url>" --country gb      # prices in another country's store
```

If the game it picked is not the one asked about, run it again with the app id
from "Other matches". Prices are US dollars unless `--country` says otherwise.

Do not use web search for Steam prices, reviews or Deck ratings: this reads Steam
and ProtonDB directly.
