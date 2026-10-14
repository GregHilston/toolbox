# pi-permission-system config

Replaces moonpi's guards. See `dot/pi/CLAUDE.md` for the reasoning; the short
version is that moonpi's containment never checked `bash`, so it caught typos
rather than damage.

`config.json` is committed and carries no secrets. The extension itself is
declared in `nixos/modules/programs/tui/pi.nix`.

- `external_directory` asks before any access outside the session's working
  tree. Writes there always ask, so a headless worker, such as `pi-ask.py`'s,
  which has nobody to answer, cannot `edit` another repo, the live dotfiles in
  `~/Git/toolbox`, or `~/.pi/agent` (where this config and the extensions
  live). An interactive session asks before editing them from another repo.
  This extension does not check what `bash` writes.
- `external_directory_read` allows reading anything under `~/Git`, plus
  `~/.pi/agent` and pi's own install, without a prompt. A headless worker
  refused every read outside its `--dir` and answered blind.
- `path` denies `*.env`, `~/.ssh/*`, and the Reddit cookie — protection moonpi
  never offered.
- `write: ask` is the one real gap left by dropping moonpi: pi's `write` can
  blind-clobber a file, whereas `edit` cannot (it needs a unique exact
  `oldText`, which is unobtainable without reading first).
