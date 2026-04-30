# AeroSpace Dotfiles

Tiling window manager config for macOS, managed via GNU Stow.

## Known Limitation: No State Persistence

AeroSpace does **not** persist window-to-workspace assignments across restarts. When
the process is killed and restarted (e.g. during `just dr moria`), all windows lose
their workspace assignments and pile onto the default workspace.

### Upstream Issues

- [#57 — Persist workspace assignments](https://github.com/nikitabobko/AeroSpace/issues/57) (open, `discussion-needed`) — primary tracking issue
- [#70 — Save/restore layout](https://github.com/nikitabobko/AeroSpace/issues/70) (closed as duplicate of #57) — covers spatial layout, not just workspace assignment
- [#152 — Crash resume functionality](https://github.com/nikitabobko/AeroSpace/issues/152) (open)
- [#107 — Reapply on-window-detected callbacks](https://github.com/nikitabobko/AeroSpace/issues/107) (open, `good-first-issue`) — proposed `reapply-window-rules` command

### Workaround: Save/Restore Around Restarts

Since apps stay running during a nix-darwin rebuild (only AeroSpace restarts),
window IDs are stable. The `just dr` command in the nixos justfile automatically
saves window state before the rebuild and restores it after, using
`bin/aerospace-save-state.sh` and `bin/aerospace-restore-state.sh`.

The state file is written to `~/.aerospace-windows.json`.

Inspired by [this gist](https://gist.github.com/af3556/59a35c8adeed8294929f1f6f8b0e1de7).
