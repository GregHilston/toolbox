---
name: game-asset
description: Make a game prop or weapon from an idea to a reviewed, playable asset, with Greg signing off twice. Concept art in 3-4 different variants (Greg picks one), then a 3D model by TRELLIS.2 on moria, a low-poly cleanup in Blender, moving parts, a firing timeline and synthesised sounds, recorded as an mp4 with sound for Greg to approve. Use when Greg asks to make, model or concept a weapon, prop or hat for a game, or to run the art pipeline on an asset.
license: MIT
---

# Game asset: idea to approved model, with two sign-offs

Run each command in your shell (the `terminal` tool in Hermes, Bash in Claude
Code, `bash` in pi) exactly as shown: no `python3` in front, no directory.
Everything after the concept is free and local on moria. Do not use a 3D web
service, an AI sound generator or downloaded sounds instead: their licences
differ, and these tools are cleared for commercial use. The why and the
lessons are in the notes vault, `llm/ai-concept-art-pipeline.md`.

**Read the project's own rules first.** In Loser Picks that is
`docs/art/pipeline.md`, `docs/art/concept-prompting.md` (the style block every
prompt carries) and `docs/art/firing-pipeline.md`. Each asset is one folder,
`art/assets/<id>/`, holding everything below plus `asset.json`, the manifest.

## Gate 1: concept (Greg picks)

Write 2 to 4 prompts per asset that differ in idea, not just wording: a
different silhouette, era or gimmick each (a snub-nose, a long-barrel and a
chrome revolver, not three revolvers in three styles). Same style block, plain
background, even light, a slightly angled side view. Batch several assets into
one round, and keep the whole round in one folder that is committed:

```bash
openai-image.py --out /abs/art/review/<date>-<batch> --name <id>-a 'PROMPT A'
magick montage <ids>-{a,b,c}.png -font /System/Library/Fonts/Supplemental/Arial.ttf \
  -pointsize 36 -set label '%t' -tile 3x -geometry 600x400+8+8 -background white grid.png
```

Each image costs about $0.04; say the round's total and get Greg's OK first.
The folder holds every variant, `prompts.tsv` and `grid.png`: one labelled row
per asset. Send the grid, then ask with one `AskUserQuestion` holding one
question per asset: one option per variant, each described in a few words,
plus "Redo" (with a note). Greg liked this form (2026-11-13). Never pick for
him, unless he says he has no preference; then pick and say which. On a pick,
copy that image to `art/assets/<id>/concept.png` and write its prompt, model,
size, cost and approval date into `asset.json` under `concept`. Unpicked
variants stay in the review folder for later. Model only the picked concept.
If the image API refuses a prompt at moderation, it is not billed: reword it
as a video-game object, or swap in a different idea.

## Build (no gate; run straight through)

```bash
game-model.py art/assets/<id>                       # TRELLIS.2 in ComfyUI, about 2 min; writes raw.glb
game-clean.py art/assets/<id> --length 1.5          # weld, 4 concept colours, 1,000 triangles, model.glb
game-clean.py art/assets/<id> --length 1.5 --flip   # rerun when the muzzle ends up at the back
game-clean.py art/assets/<id> --length 1.5 --voxels 120   # rerun when the model comes out in shards
game-turntable.py art/assets/<id>                   # turntable.png, four views
game-part.py art/assets/<id> --probe                # heights along the barrel, to find a part's box
game-part.py art/assets/<id> Hammer --y -0.37 -0.20 --z-above 0.118
```

Cleanup comes before parts and motion: the parts, the `Muzzle` marker and the
recoil are set on the final mesh, so decimating later would break them.
`--length` is the real size of the longest side in metres. Look at the
turntable yourself: the muzzle must be at the front and the shape must match
the concept. The turntable can't show which end the `Muzzle` marker is on, so
tile the clip's first second (`ffmpeg ... -vf fps=10,tile=6x2`) and check the
smoke leaves the barrel; the revolver needed `--flip` (2026-11-13). TRELLIS.2 takes 2 to 12 minutes depending on the shape; boxy
shapes are slowest. Don't switch to Hunyuan3D (`--tool hunyuan`) for a shipped
asset: its licence bars the EU, UK and South Korea.

## Motion and sound

```bash
game-sfx.py boom art/assets/<id>/sfx/bang.wav
game-sfx.py sizzle art/assets/<id>/sfx/fuse.wav --seconds 1.5
game-sfx.py click art/assets/<id>/sfx/hammer.wav
game-sfx.py pew art/assets/<id>/sfx/pew.wav --pitch 1.3
game-fire-clip.py --example
game-fire-clip.py art/assets/<id>
```

`fire.json`'s `events` are one trigger pull, which the game replays per click or while held; `shots` is only the clip's repeat count. Leave throwing (Q) out: shared code does it for every weapon. `--example` prints a musket `fire.json`: timed events (sound, rotate a part,
emit or burst particles, light, recoil, bolt) and particle presets. Write the
asset's own `art/assets/<id>/fire.json` from it, then record. The clip lands
at `art/assets/<id>/fire.mp4`. A different `--seed` is a different take of
the same sound.

## Gate 2: the clip (Greg signs off)

Send `fire.mp4` and `turntable.png` to Greg and ask with `AskUserQuestion`:
approve, change the motion or sound (with a note), remodel, or back to concept.
Turn a note such as "longer fuse" or "more smoke" into numbers in `fire.json`
or `game-sfx.py` arguments, and record again. On approval, write the date into
`asset.json` under `approved`, and copy `model.glb`, `sfx/` and the `fire`
data to wherever the project's docs say game assets live.
