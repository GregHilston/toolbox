# Karabiner-Elements Dotfiles

Caps Lock remap for macOS, managed via GNU Stow. Caps Lock **never toggles caps lock**:

| Press | Sends |
| --- | --- |
| Caps Lock | `F18`, held for as long as Caps Lock is — dictation |
| Shift + Caps Lock | `F19` — FluidVoice's Command Mode (macOS only) |
| Option + Caps Lock | `F20` — FluidVoice's Write Mode (macOS only) |

A plain remap, no tap/hold timing, so the key goes down the moment Caps Lock does. On
citadel and moria FluidVoice owns all three (`nixos/modules/darwin/fluidvoice.nix`) in its
"automatic" mode: a tap toggles hands-free recording, a hold is push-to-talk. Escape on its
own key cancels a recording. The Linux half is `services.keyd` in
`nixos/modules/common/keyd.nix`, where Handy takes `F18`; the modifier variants have no
keyd equivalent.

The modifier manipulators sit first because the plain one accepts any modifier. Karabiner
drops the mandatory modifier from the key it sends, so FluidVoice sees plain `F19`/`F20`.

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
links just `karabiner.json` — the broken case, and it exits 0, so nothing warns you at
stow time. The `stowDotfiles` activation in `nixos/modules/programs/tui/zsh/` checks for
this after the fact and prints a warning. To fix, quit Karabiner, then:

```bash
mv ~/.config/karabiner ~/.config/karabiner.pre-stow
cd ~/Git/toolbox/dot && just stow karabiner
```

Because the directory is a symlink into the repo, Karabiner's own UI edits land in the
working tree as git diffs — commit or discard them. Karabiner 16.1 loaded this file as
written without rewriting it, so the minimal form here is stable; if you change something
through the UI it may normalize on save (filling in `devices`, `fn_function_keys`,
`simple_modifications` and extra `global` keys), which is expected rather than corruption.
Its `automatic_backups/` and UI-imported `assets/` output is gitignored.

## Setup and per-host caveats

The one-time GUI steps (Karabiner's driver extension + Input Monitoring, FluidVoice's
onboarding and permission grants) are in
`nixos/docs/darwin-post-deploy.md`, which `just checklist` prints. macOS gates all of it
behind TCC prompts and per-app state, so nix can't declare any of it.

- **Until the driver extension is approved on a host, Karabiner is inert there** and Caps
  Lock keeps toggling caps. On headless **dungeon** that approval needs a VNC session.
- **FluidVoice launching and hotkeys are declarative, its permissions aren't.**
  `nixos/modules/darwin/fluidvoice.nix` seeds the hotkeys and launches it at login; check
  with `launchctl list | grep org.nixos.fluidvoice` and `~/Library/Logs/fluidvoice.log`.
- **citadel is a work-managed Mac.** If MDM policy blocks driver/system extensions,
  Karabiner won't load there at all. Nothing to do about it from this repo.
- **Dictation apps see `fn+F18`, not `F18`.** macOS stamps the function-key flag on every
  F-key event; this config does not send it. Handy stored its binding as `fn+f18` for that
  reason, and the FluidVoice seed binds both forms.
- If a long dictation ever re-triggers itself, the cause is macOS auto-repeat on the held
  `F18`. Handle it in the dictation app; Karabiner's `"repeat": false` is no fix, since
  the held key is what push-to-talk listens for.

## Troubleshooting

Karabiner 16 renamed its internals, so older advice (and the process name `karabiner_grabber`)
no longer matches — that rename is also what broke nix-darwin's `services.karabiner-elements`.
What to actually look for:

```bash
pgrep -lf "Karabiner-Core-Service"        # the privileged grabber, under its 16.x name
systemextensionsctl list | grep -i pqrs   # want [activated enabled]
grep -iE "load|grabbed|error" /var/log/karabiner/core_service.log
```

A healthy load logs `Load ~/.config/karabiner/karabiner.json...` followed by
`hid queue value monitor is started (grabbed)` for each keyboard — every keyboard needs its
own grab, so check yours is listed if a remap works on one board but not another.
