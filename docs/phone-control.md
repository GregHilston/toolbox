# Steering terminal sessions from the phone

**Update 2026-11-18:** sessions moved to the Herdr desktop app, which runs on herdr-core, so the Herdr phone app now works. The Pixel reaches moria and dungeon, never citadel (citadel accepts no inbound SSH). The rest of this page is the earlier research, for when the TUI was the plan.

Researched 2026-11-16. Verdict: **no tool clears the bar yet.** The best route is
Termux on the Pixel, SSH to the machine, then `zj <name>`. It lands in the real zellij
session.

## What we want

Watch and reply to each Claude session from the Pixel, keeping zellij + the Herdr TUI
(chosen over the Herdr desktop app for the zellij hotkeys). It must survive shift
rolls. A roll sends `/clear` into the same Herdr pane (`docs/claude-shifts.md`), so
anything that attaches to the pane survives one.

## Options and why they lost

| Option | Result |
|---|---|
| Termux → `ssh ghilston@moria.tail1b9d9.ts.net` → `zj <name>` | **Best available.** Real sessions, any pane, rolls fine, nothing new installed (moria already accepts the Pixel's key). Cramped at ~50 columns, and zellij shrinks the desktop's shared tab to the phone's size ([#5624](https://github.com/zellij-org/zellij/issues/5624)). Not yet tried on the phone. |
| Herdr phone app | **Adopted 2026-11-18**, with the desktop app. Earlier: **ruled out.** It talks only to herdr-core (`hc`), never to the TUI's server, on purpose ([herdr-app#63](https://github.com/herdrdev/herdr-app/issues/63)). TUI panes never show. Using it means running sessions under `hc` instead, in a second place. Revisit if the TUI moves onto herdr-core. |
| zellij web client | **Out for now.** Android typing is buggy (fix [#5890](https://github.com/zellij-org/zellij/pull/5890) merged after 0.46.0). A browser reconnect can resurrect a session as a second server and orphan the original ([#5762](https://github.com/zellij-org/zellij/issues/5762), open). Revisit once a release has both fixed. Needs TLS (`tailscale serve`). |
| Claude Remote Control | One process at a time, weak status view, loses track across rolls. |
| `herdr --remote` from Termux | No Android build of herdr. |
| Happy and similar wrappers | They start their own session instead of attaching to ours. |

## herdr-core (`hc`), for the record

- The Herdr TUI does not need `hc`. citadel and foundation run the TUI without it.
- `hc` buys only the phone and desktop apps. Its `run/read/send/wait` duplicate the
  `herdr` skill but act on `hc` terminals, so the skill stays on the TUI.
- It installs by curl into `~/.local`, outside nix, and self-updates. The phone's key
  (`herdr-mobile`) can log in to every machine that accepts it.
- 2026-11-16: the phone app was uninstalled. `hc` was left running on moria and dungeon,
  and `herdr-mobile` stayed in dungeon's `~/.ssh/authorized_keys`. No `hc` on citadel,
  ever.
