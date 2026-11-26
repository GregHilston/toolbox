# Herdr, phone chats, citadel and the machines

Read this when you start or attach a session, pick a machine for a build, or Greg asks how to continue a phone chat. The global `CLAUDE.md` points here.

## Herdr pane or subagent

**A Herdr pane is for work Greg will watch or talk to; a subagent is for work behind the scenes.** Start a session in a Herdr pane (the `herdr` skill) when he may want to watch it, type into it or ask it more later: a reviewer we argue with, a pairing partner, a long job he'll check on. Research, searches, one-shot reviews and anything else that only hands back a result run as an Agent-tool subagent or through `pi-ask`, which keep their spend caps and return a clean answer. Each subagent already gets a read-only Herdr tab from the hook, so never open a pane just to make work visible.

## Where Claude runs

- Greg drives Claude from Herdr, the desktop app or the TUI.
- Claude runs in a Herdr pane, never straight in zellij: there Herdr can't see it and shows no working or idle state (2026-11-12). zellij sessions (`zj <name>`) no longer start Herdr on their own (2026-11-18). moria lists dungeon's workspaces too (`herdr machine add`).

## Phone chats

A chat Greg starts fresh from his phone runs on moria in SDK mode (`entrypoint: sdk-cli` in its transcript), gets no title, and `/resume` hides it. One started with `claude` in a terminal on moria, then attached with `/remote-control`, shows up in `/resume` like any other. Point him at that when he asks how to continue a phone chat on the laptop (2026-11-08). SDK mode also drains the 5-hour window faster; see `claude-model-picking.md`.

Don't say a message reached another session until it says so. A headless session holds `SendMessage`, and Greg can't see or reach it; he prefers a session he can open (#674, gridkeep).

## Citadel

On citadel, his Mozilla laptop, agents never write to tickets or PRs. He wants that physically impossible; until the lockdown in `~/Git/notes/llm/herdr-rollout-plan.md` is done, the rule in `CLAUDE.md` is the only guard. When the bug is on citadel, ask once for SSH before sending commands to paste: on 2026-11-12, three rounds of pasted output led nowhere, and its tab-1 bug fell within minutes of SSH.

## moria and dungeon

- **moria** is the M4 Max (16 cores, 128 GB) Greg develops on, and Claude usually runs on it. It is dev-only, so use all its hardware.
- It sleeps when idle, which stalls long runs (on 2026-10-21 it slept when he undocked it, despite his keep-awake app). Start `caffeinate -dims -t 43200` in the background before a long run.
- **dungeon** is the home lab (M3 Pro, 36 GB, RAM nearly full) running services that must not be interrupted. Put no build or test load on it. Run `hostname -s` before the first build: on 2026-11-06 a session on dungeon took itself for moria and built there all afternoon. `hooks/no-build-on-dungeon.py` now blocks builds and tests there; send them to moria with `ssh moria`.
- When another machine can't ssh to moria over Tailscale but `tailscale ping` answers, run `tailscale down; tailscale up` on moria (no sudo, no exit node); its extension stopped passing inbound TCP on 2026-11-17. moria's LAN address `192.168.1.31` is the fallback.
