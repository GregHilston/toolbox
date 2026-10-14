# pi-permission-system config

Replaces moonpi's guards. See `dot/pi/CLAUDE.md` for the reasoning; the short
version is that moonpi's containment never checked `bash`, so it caught typos
rather than damage.

`config.json` is committed and carries no secrets. The extension itself is
declared in `nixos/modules/programs/tui/pi.nix`.

- `external_directory` — the two repos that are two halves of one system stay
  allowed, matching the cross-repo access added earlier. Everything else asks.
- `external_directory_read` allows reading anything under `~/Git` without a
  prompt. A headless worker, such as `pi-ask.py`'s, has nobody to answer a
  prompt, so every read outside its `--dir` was refused and it answered blind.
  Writes outside the working tree still ask, which a headless worker can't, so
  they stay blocked.
- `path` denies `*.env`, `~/.ssh/*`, and the Reddit cookie — protection moonpi
  never offered.
- `write: ask` is the one real gap left by dropping moonpi: pi's `write` can
  blind-clobber a file, whereas `edit` cannot (it needs a unique exact
  `oldText`, which is unobtainable without reading first).
