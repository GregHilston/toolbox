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
openai-image.py --ref /abs/approved.png 'PROMPT'               # match a reference image's style (edits endpoint)
openai-image.py --quality high 'PROMPT'                         # about 4x the cost; only when asked
```

The model has no transparent background; ask for a plain flat mid-grey one and
key it out later. A reference image costs about 15 times the input tokens and,
in the first test, matched what the prompt alone gave, so use it only when a
prompt fails to hold the style.

Every call costs money: medium measured 1,372 output tokens (about $0.04) at
1536x1024 or 1024x1536 and 1,756 (about $0.05) at 1024x1024; high is about four
times that. Stay at medium unless Greg asks for high, and make only the
variants the task needs. The account has a spend cap; a 429 may mean it is
reached, so say so rather than retrying.

Put the prompt in single quotes and write it without apostrophes. For
Loser Picks concept art, build the prompt from that repo's
`docs/art/concept-prompting.md`.

The output has one `MEDIA:` line per image. In Hermes, end your reply with
those lines as printed; in Claude Code, read the PNGs to see them; in pi, give
the paths. Do not use `curl`, a web search or the ChatGPT Plus endpoint
instead.
