# Attic

Things deleted from this repo, and how to get them back.

Nothing here is lost — git has all of it. This file exists so that "wait, was that
important?" is a `git show` away instead of an archaeology session.

To recover a file: `git show <sha>^:<path> > <path>`
To see it in context: `git show <sha>`

## 2026-08-15 — repo cleanup

The repo started in 2013 as general dotfiles and became a NixOS/nix-darwin config repo.
These are the layers that were never removed.

| What | Path | Removed in | Why |
| --- | --- | --- | --- |
| yabai config | `dot/yabai/.yabairc` | `10a9a69` | Superseded by AeroSpace. Last real edit 2022-03. |
| skhd config | `dot/skhd/.skhdrc` | `10a9a69` | Body was entirely `yabai -m ...`; dead with yabai. Would have fought the live AeroSpace bindings if stowed. |
| redshift config | `dot/redshift/.config/redshift.conf` | `10a9a69` | Linux X11 only. Last real edit 2022-01. |
| i3 config | `dot/i3-pkg/` | `10a9a69` | Last real edit 2022-07. |
| i3-gaps config + builder | `dot/i3-gaps-pkg/` | `10a9a69` | Its host fragments targeted isengard and foundation; both run KDE Plasma now. Also the source of the `~/src` symlink bug. |
| `just build-i3-gaps` | `dot/justfile` | `10a9a69` | Built the above. |
| WSL font screenshots | `docs/res/*.png` | `5d2749e` | 1.3 MB serving one README section. |
| Windows font walkthrough | `README.md` section | `5d2749e` | Fonts come from stylix now. |
| Shell/vim cheat sheet | `docs/CHEAT_SHEET.md` | `5d2749e` | Orphaned, and documented a vim-plug setup that has no package in `dot/`. |
| nixos `/commit` command | `nixos/.claude/commands/commit.md` | `f143a25` | Shadowed the richer global `claude-commands/commit.md` with a Linux-only copy. **Its `--push` / `--pr` flags went with it** — use `gh pr create`. |
| nix-fmt PostToolUse hook | `nixos/.claude/hooks/PostToolUse.md` | `f143a25` | A markdown file in `hooks/`; Claude Code reads hooks from `settings.json`, which has no `hooks` key. Never executed. Re-adding it properly is an open follow-up. |
| Audio transcribe/ask | `bin/audio-transcript.py`, `bin/audio-ask.py` | `7ea9e65` | The *logic* moved to `roger/roger/audio/{transcribe,ask}.py`. **The CLI did not** — see the note below. |
| Pixel 8 (Termux) block | `CLAUDE.md` | `657eeac` | Duplicate of the block in the global `dot/claude/.claude/CLAUDE.md` — same paths and port, differing only in one label ("SSH config:" vs "SSH:"). Both files load in every session in this repo. |
| Unused vars fields | `nixos/config/vars.nix` | `d2f569f` | `paths.{dotfiles,configHome,dataHome,cacheHome}`, `networking.domain`, `user.packages.{terminal,editor}`, `system.stateVersion`. See the commit for why `stateVersion` was a trap rather than merely unused. |

### Capability genuinely lost: one-shot audio transcription from the shell

`roger/roger/audio/{transcribe,ask}.py` are **importable library modules** — no `__main__`,
no argparse/typer. `roger`'s console scripts are `roger` and `generate-schema`, and
`roger/cli.py` has no `transcribe` or `ask` command. The only consumers are async 202 job
endpoints (`roger/api/routes/audio.py`), which need `roger serve` running plus a curl-and-poll
loop, and the Slack bot.

So these no longer have an equivalent one-liner:

```bash
audio-transcript.py file.m4a > transcript.txt     # transcript on stdout, pipeable
audio-ask.py video.mp4 "summarize this"
```

Also gone: the `--start` / `--end` trim flags, `--agent claude`, and the `--chat`
interactive handoff.

Nothing in the toolbox referenced these scripts, so nothing errors — the commands are just
gone. To restore either one:

```bash
git show 7ea9e65^:bin/audio-transcript.py > bin/audio-transcript.py && chmod +x bin/audio-transcript.py
```

The durable fix is a `roger transcribe` / `roger ask` Typer command wrapping the existing
library functions, which would make the deletion genuinely a supersession.

### Considered and deliberately kept

- **`windows/`** — `autounattend.xml` is cheap to keep and unreproducible if that machine
  is ever reinstalled. The Windows box also still hosts `foundation`.
- **`networking.hosts.{pihole1,pihole2,proxmox}`** in `vars.nix` — no code reads them, but
  `vars.nix` is the documented home for host IPs and the block comment already allows for
  entries that aren't ssh targets. Reference data, not dead code.
- **`paths.nixosFlake`** — looked unused at a glance; it is read by `programs/tui/nh.nix`
  and `modules/home/workstation.nix`.
- **The `enableGui` *claim*** in `nixos/CLAUDE.md` — flagged as stale during review, but it
  is accurate: `enableGui` is still a real binding in `modules/home/default.nix`. The
  surrounding sentence was still edited in `484c9cd` to drop a non-existent `alacritty`
  module and to say explicitly that `enableGui` reads `osConfig.custom.desktop.enable`;
  what was kept is the claim, not the exact wording.

### Known to be stale, not addressed here

- `bin/anki/README.md` refers to an `/anki` Claude Code skill that does not exist in
  `claude-skills/`. It presumably lives in the private notes repo; unresolvable from here.
- `nixos/scripts/setup-nfs-mount.sh` has no justfile recipe and is referenced only from
  `nixos/README.md`.
- `hosts/macs/dungeon/default.nix` is 427 lines and holds 10 launchd agents — genuinely
  under-modularized, but splitting it is a refactor with rebuild risk, not cleanup.
