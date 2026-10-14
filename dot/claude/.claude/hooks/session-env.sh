#!/bin/bash
# Give Claude Code's Bash tool the toolbox PATH and secrets a terminal has.
#
# A SessionStart hook. Claude Code's shell snapshot ends by exporting its own
# PATH, which undoes ~/.zshenv, and a session the desktop app started never
# read ~/.zshrc's secrets. Claude Code runs $CLAUDE_ENV_FILE before every
# Bash command, after the snapshot, so the lines written here stick.
# The secrets stay in their gitignored file; this only names it.
set -euo pipefail
IFS=$'\n\t'

[[ -n "${CLAUDE_ENV_FILE:-}" ]] || exit 0
marker='# toolbox session env'
# resume and compact fire this again
grep -qsxF "$marker" "$CLAUDE_ENV_FILE" && exit 0

toolbox="${TOOLBOX_HOME:-$HOME/Git/toolbox}"
[[ -d "$toolbox/bin" ]] || exit 0
# Same set as .zshenv's bin/**/*(/N): no hidden dirs.
dirs=$(find "$toolbox/bin" \( -name '.*' -o -name __pycache__ \) -prune -o -type d -print | paste -sd: -)
secrets="$toolbox/nixos/secrets/.env"

{
  echo "$marker"
  echo "export PATH=\"\$PATH:$dirs\""
  echo "[ -f '$secrets' ] && { set -a; . '$secrets'; set +a; }"
} >> "$CLAUDE_ENV_FILE"
