# Karabiner-Elements Dotfiles

Caps Lock remap for macOS, managed via GNU Stow. Caps Lock **never toggles caps lock**:

| Gesture | Result |
| --- | --- |
| quick tap (< 250ms) | `Escape` |
| hold (> 250ms) | `F18` held for as long as you hold Caps Lock — Handy's push-to-talk key |

The Linux half of the same behavior is `services.keyd` in `nixos/modules/common/keyd.nix`;
both platforms emit `F18` so Handy has one hotkey everywhere.

## Retuning the thresholds

The two parameters under `complex_modifications.parameters` must stay **equal to each
other**, and matched to keyd's single `timeout(esc, N, f18)`. Three literals, one number.

- `basic.to_if_held_down_threshold_milliseconds` is the real tap/hold split, and the only
  one keyd has an equivalent for.
- `basic.to_if_alone_timeout_milliseconds` is the window in which a release still counts as
  a tap. Karabiner's default is 1000ms. Raising it **above** the hold threshold risks
  emitting `Escape` *in addition to* `F18` on a hold — a stray Escape into whatever you're
  dictating at, which is the exact failure this design exists to avoid.

250ms is a deliberate compromise. Lower makes it easy to overshoot while reaching for
Escape, which swallows the Escape and fires a useless sub-10ms recording; higher delays the
start of dictation. Overshooting costs more than the delay does, since a hold lasts seconds
anyway.

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

The one-time GUI steps (Karabiner's driver extension + Input Monitoring, Handy's
Microphone/Accessibility grants, and setting Handy's hotkey to `F18`) are in
`nixos/docs/darwin-post-deploy.md`, which `just checklist` prints. macOS gates all of it
behind TCC prompts and per-app state, so nix can't declare any of it.

- **Until the driver extension is approved on a host, Karabiner is inert there** and Caps
  Lock keeps toggling caps. On headless **dungeon** that approval needs a VNC session.
- **Handy launching is declarative, its permissions aren't.** A launchd agent
  (`nixos/modules/darwin/handy.nix`, on citadel and moria) runs `open -g -j -a Handy` at
  login; check it with `launchctl list | grep org.nixos.handy` and read
  `~/Library/Logs/handy.log` if it didn't come up. Leave Handy's own "Launch at login"
  setting off so both aren't registering it. dungeon has the cask but not the agent.
- **citadel is a work-managed Mac.** If MDM policy blocks driver/system extensions,
  Karabiner won't load there at all. Nothing to do about it from this repo.
- **Handy stores the binding as `fn+f18`, not `f18`.** That's correct: macOS stamps the
  function-key flag on every F-key event, so `fn` is what the OS reported while the picker
  was capturing, not something this config sends. It matches at runtime. If a future version
  ever fails to match, plain `"f18"` in Handy's `settings_store.json` is the fallback.
- If Handy's shortcut picker refuses `F18` outright, switch this file and the keyd config to
  a hyper combo instead — `command+control+option+shift+d` here, `C-A-S-d` in keyd.
- If a long dictation ever re-triggers itself, the cause is macOS auto-repeat on the held
  `F18` (Karabiner's `repeat` defaults to true, which is *also* what makes the key stay
  held — so don't "fix" it with `"repeat": false`, which would turn the hold into a tap).
  Handle it with `hold_down_milliseconds` or on Handy's side.

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
