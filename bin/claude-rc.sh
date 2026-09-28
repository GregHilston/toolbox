#!/bin/bash
# Serve one ~/Git repo to the Claude app over Remote Control.
#
# dungeon runs one per repo as a launchd agent; moria runs them in zellij
# (`rc` in .zshrc). Each session the app spawns gets its own git worktree,
# except in the notes vault: its edits belong on main, not on a branch nobody
# merges. Permission mode defaults to auto because dungeon's sessions have the
# Docker socket of the whole lab; moria's layout asks for bypass.
set -euo pipefail
IFS=$'\n\t'

repo=${1:?usage: claude-rc.sh <repo under ~/Git>}

# launchd's PATH has none of these.
export PATH="$HOME/.orbstack/bin:$HOME/.local/bin:/etc/profiles/per-user/$(id -un)/bin:/run/current-system/sw/bin:/opt/homebrew/bin:$PATH"

spawn=worktree
[[ $repo == notes ]] && spawn=same-dir

# Nothing runs direnv here. Not `direnv exec`: it also exports every secret.
[[ $repo == home-lab ]] && export COMPOSE_ENV_FILES=.env,secrets/.env

cd "$HOME/Git/$repo"
exec claude remote-control \
  --name "$(hostname -s)/$repo" \
  --spawn "$spawn" \
  --permission-mode "${CLAUDE_RC_PERMISSION_MODE:-auto}"
