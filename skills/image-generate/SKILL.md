---
name: image-generate
description: Make an image from a description with FLUX.2 klein on moria's GPU, about 20 seconds, and attach it. Use when asked to draw, paint, imagine, picture or generate an image or art, and for follow-ups that change one (make them zebras, wider, at night).
license: MIT
---

# Image generation

One command, already on `PATH`. Run it in your shell (the `terminal` tool in
Hermes, Bash in Claude Code, `bash` in pi) exactly as shown: no `python3` in
front and no directory. It is not a tool itself.

```bash
comfy-image.py "PROMPT"                              # 1024x1024, a new random seed
comfy-image.py --seed 531322723 "PROMPT"             # same composition, changed prompt
comfy-image.py --width 1344 --height 768 "PROMPT"    # landscape; 768x1344 portrait
```

## Write the prompt yourself

Never pass the user's words through as they are. Turn them into one paragraph
of plain description, 40 to 80 words: the subject and what it is doing, the
setting, the medium or style, the lighting, the colours, the composition.
Describe only what should be in the picture; there is no negative prompt.

> watercolor of buffalo playing basketball →
> A loose watercolor painting of two American bison playing basketball on an
> outdoor court at golden hour, one leaping for a slam dunk, soft wet-on-wet
> washes, visible paper texture, warm ochre and blue palette

Words that must appear in the picture go in double quotes inside the prompt,
and keep them short: the model misspells long text.

## Follow-ups change the last image

When the user asks for a change ("make them zebras", "at night", "wider"),
find the prompt and seed of the last image in this conversation, edit only
what they asked for, and run again with that `--seed` so the rest stays put.
Use a new seed only when they want something different or another try.

## Reply

The output ends with a `MEDIA:` line. Show the prompt you used in one short
line, then:

- **Hermes**: end your reply with that `MEDIA:` line exactly as printed, on its
  own line. That is what attaches the image.
- **Claude Code**: read the PNG with the Read tool to see it, and give the path.
- **pi**: give the path.

If it says moria is asleep or unreachable, say so; there is no other image
generator to fall back on. Do not use web search or `curl` for this.
