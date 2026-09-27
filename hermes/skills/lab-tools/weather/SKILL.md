---
name: weather
description: Current weather and the forecast for home (Sheldon, VT) or any named town, no key needed. Use for any question about weather, temperature, rain or snow.
version: 1.0.0
author: Greg Hilston
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [weather, forecast]
    requires_toolsets: [terminal]
---

# Weather

One command, already on `PATH`. Run it with the `terminal` tool exactly as
shown: no `python3` in front and no directory. It is not a tool itself.

```bash
weather.py                                   # home: now, then today and the next 2 days
weather.py --days 7                          # up to 16 days
weather.py --place "Burlington, VT"          # any town; add a state or country after a comma
```

With no `--place` it is home. Temperatures are °F, rain and snow in inches.

Do not use web search for weather: this is current and exact.
