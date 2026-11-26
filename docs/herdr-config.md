# Configuring and testing Herdr

Read this before changing Herdr's config, keys or hooks, or testing a TUI under it. Toolbox's `CLAUDE.md` points here; why Herdr, with results: `~/Git/notes/llm/herdr-rollout-plan.md` and `herdr-trial.md`.

- Herdr runs on every host: Homebrew on Macs, nix on NixOS, config in `dot/herdr/`. The desktop app is the `herdr-app` cask on Macs and `herdr-desktop` on NixOS GUI hosts. Its terminals set `HC_TERMINAL_ID` (and no `HERDR_*`); its CLI is `hc`, which takes status from the program's own OSC 7501 output, not from env.
- `dot/claude/.claude/hooks/herdr-subagent.sh` gives each Agent-tool subagent a tab and sidebar row. It exits at once outside Herdr. Its task and model come from Claude's undocumented `subagents/agent-<id>.meta.json`.
- Subagent tabs only show a transcript. For a session agents can message, `skills/herdr` wraps `herdr --skill` (`agent start`, `agent prompt`, `agent read`) in the TUI and `hc run/send/wait/read` in the desktop app.
- The desktop app's keys and the `Ctrl+B` prefix mod (`tmux-prefix`, zellij's tmux mode) live in `dot/herdr-app/`, stowed on Macs only. The app recreates a missing `keys.json` at once, so replace a real one with `ln -sfh` then `mv -f`, not `rm` then stow.
- Restart the server after changing `keys.prefix`; `herdr server reload-config` did not make a new prefix work.
- Before binding a key, check `dot/aerospace/.aerospace.toml` and `dot/zellij/` for it. AeroSpace owns `Alt` and `Alt+Shift`, zellij owns `Ctrl+B`, so Herdr's direct keys are `Ctrl+Alt`. `Ctrl+Alt+/` pops up `cheatsheet.txt`; update it with each binding.
- Anything in `.zshrc` that takes the terminal belongs above p10k's instant prompt: a Herdr started below it never draws.
- To test a TUI in zellij, open a real window (`open -na Ghostty --args -e /bin/zsh -lic '…'`) and read it with `zellij -s <s> action dump-screen --pane-id terminal_0`. A Python pty can't answer Herdr's terminal queries, and from inside Herdr, strip `HERDR_*` first, or Herdr refuses to nest.
- The Herdr phone app sees only `hc` terminals, not TUI panes; TUI phone access is Termux + `ssh` + `zj`. Options weighed: `docs/phone-control.md`.
