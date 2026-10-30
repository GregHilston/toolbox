#!/usr/bin/env bash
# Give Claude Code's Bash tool the toolbox PATH and the LLM gateway keys.
#
# A SessionStart hook. Claude Code's shell snapshot ends by exporting its own
# PATH, which undoes ~/.zshenv, and a session the desktop app started never
# read ~/.zshrc's secrets. Claude Code runs $CLAUDE_ENV_FILE before every
# Bash command, after the snapshot, so the lines written here stick.
# Only the two keys pi-ask and the overnight loop need: every child,
# including workers reading untrusted pages, inherits them. The values
# stay in their gitignored file; this only names it.
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

cat >> "$CLAUDE_ENV_FILE" <<EOF
$marker
export PATH="\$PATH:$dirs"
[ -f '$secrets' ] && eval "\$(sed -nE 's/^(export )?((LITELLM|DEEPSEEK|OPENCODE)_API_KEY=)/export \2/p' '$secrets')"
EOF
