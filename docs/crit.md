# Crit: review agent plans and diffs in a browser

Read this before changing how crit is installed, shared or styled. Toolbox's `CLAUDE.md` points here.

- The package comes from its flake in `nixos/modules/home/workstation.nix`; the Claude plugin is in `settings.json`.
- Sharing to crit.md is off: `share_targets = []` in that module, and `shims/crit` refuses `share` and `auth`, since `--share-url` beats the config.
- crit has no auth, so it stays on loopback; `crit-remote.py <host>` opens another host's review over an SSH tunnel.
- Styling is `~/.crit/custom.css` in that module, `--crit-*` variables only (crit's README: class names are not a stable API).
- Palette, width and line numbers live in a browser cookie, not config: set them per browser in Settings → Display (Catppuccin Mocha / GitHub Light Default, Compact, numbers off).
