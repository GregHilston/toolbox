#!/usr/bin/env bash
# notes-vault-autocommit.sh
#
# Claude Code Stop hook for the Obsidian vault at ~/Git/notes.
# When the vault has uncommitted changes, regenerate the roger index/tags
# (best-effort) and then auto-commit + push.
#
# Wired on this machine only via ~/Git/notes/.claude/settings.local.json
# (gitignored) so it never runs on machines without roger + oMLX — e.g. the
# Termux/Pixel checkout, where it would just fail.
#
# Design:
#   * Fast no-op when the working tree is clean (cheap `git status` guard).
#   * roger index is best-effort: if oMLX is down or errors, still commit the
#     note changes so nothing is lost.
#   * Reads the oMLX API key from the gitignored roger/.env.local and forces the
#     light gemma-4 E4B model for fast summarisation.
set -uo pipefail

NOTES="${HOME}/Git/notes"
ROGER="${HOME}/Git/home-lab/roger"

# Nothing to do if the vault working tree is clean.
[ -n "$(git -C "$NOTES" status --porcelain 2>/dev/null)" ] || exit 0

# Regenerate the auto-managed _vault-*.md (best-effort — never block the commit).
if [ -d "$ROGER" ] && command -v uv >/dev/null 2>&1; then
  (
    cd "$ROGER" || exit 0
    set -a
    [ -f .env.local ] && . ./.env.local
    set +a
    ROGER_MODEL="openai:gemma-4-e4b-it-qat-4bit" uv run roger index
  ) >/dev/null 2>&1 || true
fi

# Commit + push whatever changed.
git -C "$NOTES" add -A
git -C "$NOTES" diff --cached --quiet && exit 0   # nothing staged after all
git -C "$NOTES" commit -q -m "chore(vault): auto-update via roger index [$(date '+%Y-%m-%d %H:%M')]" || exit 0
git -C "$NOTES" push -q || true
exit 0
