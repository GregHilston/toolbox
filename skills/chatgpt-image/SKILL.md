---
name: chatgpt-image
description: Make an image with ChatGPT's image model on Greg's Plus plan, headless, about 30 seconds each and no extra cost. Use for concept art, game assets and anything where getting the object right matters more than speed; image-generate (FLUX on moria) is faster for loose sketches.
license: MIT
---

# ChatGPT image generation

One command, already on `PATH`. Run it in your shell (the `terminal` tool in
Hermes, Bash in Claude Code, `bash` in pi) exactly as shown: no `python3` in
front and no directory.

```bash
chatgpt-image.py 'PROMPT'                                   # model picks the size
chatgpt-image.py --size 1536x1024 'PROMPT'                  # landscape; 1024x1536 portrait, 1024x1024 square
chatgpt-image.py --out /abs/dir --name musket 'PROMPT'      # save as /abs/dir/musket.png
```

Put the prompt in single quotes and write it without apostrophes. Describe the
picture in plain words: subject, style, background, view. It follows long
prompts and short sign text well.

It uses the Plus allowance that Luna shares, so run batches of at most about 20
and read `deepseek-preflight.py`'s Luna line before a bigger one. It runs one
image at a time; start several in parallel for a batch.

The output ends with a `MEDIA:` line naming the PNG. In Hermes, end your reply
with that line as printed; in Claude Code, read the PNG to see it; in pi, give
the path. If it says the login expired or was refused, say so and point to
home-lab's `docs/runbooks/llm-chatgpt-login.md`. Do not use `curl`, a web
search or another image tool instead.
