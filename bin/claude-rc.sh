#!/bin/bash
# Serve one ~/Git repo to the Claude app over Remote Control.
#
# dungeon runs one per repo as a launchd agent; moria runs them in zellij
# (`rc` in .zshrc). Each session the app spawns gets its own git worktree,
# except in the notes vault: its edits belong on main, not on a branch nobody
# merges. `direnv exec` gives sessions the repo's .envrc, which nothing else
# loads here — home-lab's COMPOSE_ENV_FILES above all.
set -euo pipefail
IFS=$'\n\t'

repo=${1:?usage: claude-rc.sh <repo under ~/Git>}

# launchd's PATH has none of these.
export PATH="$HOME/.orbstack/bin:$HOME/.local/bin:/etc/profiles/per-user/$(id -un)/bin:/run/current-system/sw/bin:/opt/homebrew/bin:$PATH"

spawn=worktree
[[ $repo == notes ]] && spawn=same-dir

cd "$HOME/Git/$repo"
exec direnv exec . claude remote-control \
  --name "$(hostname -s)/$repo" \
  --spawn "$spawn" \
  --permission-mode "${CLAUDE_RC_PERMISSION_MODE:-bypassPermissions}"
