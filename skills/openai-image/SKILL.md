---
name: openai-image
description: Make images with OpenAI's gpt-image-2 through the paid Images API at a fixed quality, about 4 US cents each at medium. Use for game concept art and any image where the object must be right and every image must match in quality; image-generate (FLUX on moria) is free and faster for loose sketches.
license: MIT
---

# OpenAI image generation

One command, already on `PATH`. Run it in your shell (the `terminal` tool in
Hermes, Bash in Claude Code, `bash` in pi) exactly as shown: no `python3` in
front and no directory.

```bash
openai-image.py 'PROMPT'                                        # medium, 1536x1024
openai-image.py --size 1024x1536 'PROMPT'                       # portrait; 1024x1024 square
openai-image.py --n 3 --out /abs/dir --name musket 'PROMPT'     # three variants, musket-1.png ...
openai-image.py --quality high 'PROMPT'                         # about 4x the cost; only when asked
```

Every call costs money: medium is about $0.04 an image at 1536x1024 and high
about $0.17. Stay at medium unless Greg asks for high, and make only the
variants the task needs. The account has a spend cap; a 429 may mean it is
reached, so say so rather than retrying.

Put the prompt in single quotes and write it without apostrophes. For
Loser Picks concept art, build the prompt from that repo's
`docs/art/concept-prompting.md`.

The output has one `MEDIA:` line per image. In Hermes, end your reply with
those lines as printed; in Claude Code, read the PNGs to see them; in pi, give
the paths. Do not use `curl`, a web search or the ChatGPT Plus endpoint
instead.
