---
name: steam-game
description: A Steam game's price and discount, review score, Steam Deck rating, and Linux/ProtonDB support, no key needed. Use for any question about a PC game on Steam.
version: 1.0.0
author: Greg Hilston
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [steam, games, steam-deck, linux]
    requires_toolsets: [terminal]
---

# Steam games

One command, already on `PATH`. Run it with the `terminal` tool exactly as
shown: no `python3` in front and no directory. It is not a tool itself.

```bash
steam-game.py "<game name>"                   # the best match, and other matches
steam-game.py <app id>                        # an exact game, e.g. 1145360
steam-game.py "<store url>" --country gb      # prices in another country's store
```

If the game it picked is not the one asked about, run it again with the app id
from "Other matches". Prices are US dollars unless `--country` says otherwise.

Do not use web search for Steam prices, reviews or Deck ratings: this reads Steam
and ProtonDB directly.
