---
name: wikipedia
description: Look things up on Wikipedia: an article's summary, or a list of matching articles. Use for facts about people, places, things and events.
version: 1.0.0
author: Greg Hilston
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [wikipedia, research, reference]
    requires_toolsets: [terminal]
---

# Wikipedia

One command, already on `PATH`. Run it with the `terminal` tool exactly as
shown: no `python3` in front and no directory. It is not a tool itself.

```bash
wikipedia.py "<topic>"                    # the article's summary and link
wikipedia.py --search "<words>"           # matching articles, when unsure of the name
wikipedia.py --lang fr "<topic>"          # another language's Wikipedia
```

A topic that is not an exact title still finds the closest article, and lists
the others. When the summary is not enough, read the whole article with the
`read-page` skill's command on the link it prints, if you have that skill.

Do not use web search to reach Wikipedia.
