# Karabiner-Elements Dotfiles

Caps Lock remap for macOS, managed via GNU Stow. Caps Lock **never toggles caps lock**:

| Gesture | Result |
| --- | --- |
| quick tap (< 200ms) | `Escape` |
| hold (> 200ms) | `F18` held for as long as you hold Caps Lock — Handy's push-to-talk key |

The Linux half of the same behavior is `services.keyd` in
`nixos/modules/common/handy.nix`; both platforms emit `F18` so Handy has one hotkey
everywhere. Tune the two thresholds in `.config/karabiner/karabiner.json` under
`complex_modifications.parameters`.

## Why the whole directory is symlinked, not the file

Karabiner-Elements **replaces** a symlinked `karabiner.json` with a real file when it
saves (it writes a temp file and renames over the target), and it also
[fails to notice changes](https://github.com/pqrs-org/Karabiner-Elements/issues/3248)
when the file is a symlink. Upstream's
[documented workaround](https://karabiner-elements.pqrs.org/docs/manual/misc/configuration-file-path/)
is to symlink the **`~/.config/karabiner` directory** instead — which is what stow does
by default (tree folding), so this package needs no special handling.

The catch: stow only folds the directory if `~/.config/karabiner` **doesn't exist yet**.
If Karabiner has already run on a host, stow descends into the existing directory and
links just `karabiner.json` — the broken case. Fix it by quitting Karabiner, then:

```bash
mv ~/.config/karabiner ~/.config/karabiner.pre-stow
cd ~/Git/toolbox/dot && just stow karabiner
```

Because the directory is a symlink into the repo, Karabiner's own UI edits land in the
working tree as git diffs — commit or discard them. Its `automatic_backups/` output is
gitignored.

## One-time manual setup (not declarable)

macOS gates all of this behind TCC prompts and per-app state, so nix can't do it:

1. **Karabiner**: on first launch, approve the driver extension (System Settings →
   Privacy & Security → allow, may need a reboot) and grant **Input Monitoring**.
   Karabiner's own remap supersedes System Settings → Keyboard → Modifier Keys, so
   leave that at its default.
2. **Handy**: grant **Microphone** and **Accessibility** (needed to paste transcribed
   text into the focused app), then download a model — Parakeet V3 for CPU-efficient
   English, or Whisper Turbo/Large for better accuracy and 100+ languages.
3. **Handy hotkey**: set the binding to `F18` by *holding Caps Lock* while the shortcut
   picker is capturing, and leave push-to-talk mode **on** (its default). Handy stores
   this in its own app state, not a file we manage.

If Handy's picker refuses `F18`, switch both this file and the keyd config to a hyper
combo instead — `command+control+option+shift+d` here, `C-A-S-d` in keyd.
