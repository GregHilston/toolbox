#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# sync-to-moria.sh — copy this repo's uncommitted changes to moria to commit there.
#
# I edit toolbox on this Mac but commit from moria (personal git identity), so
# working-tree changes have to land on moria's checkout first. This rsyncs the
# changed files over, previewing with --dry-run and asking before the real copy.
#
# Two things keep it simple:
#   * rsync -R (--relative) recreates each file's repo-relative path under the
#     destination, so you never spell out per-file destinations.
#   * the destination is HOME-RELATIVE (Git/toolbox/), which the remote resolves
#     against ghilston's home — so the greghilston -> ghilston home-dir difference
#     sorts itself out with no hardcoded /Users/ghilston path.
#
# Note: does NOT propagate deletions (no --delete); it copies existing files only.

REMOTE="${SYNC_REMOTE:-ghilston@moria.local}"
DEST="Git/toolbox/" # home-relative on the remote -> /Users/ghilston/Git/toolbox/

usage() {
  cat <<'EOF'
sync-to-moria.sh — rsync this repo's working-tree changes to moria

Usage:
  sync-to-moria.sh            preview all working-tree changes, confirm, then sync
  sync-to-moria.sh -y         skip the confirmation prompt
  sync-to-moria.sh FILE...    sync only the given files (repo-relative paths)

Env:
  SYNC_REMOTE   override the remote (default: ghilston@moria.local; e.g. "moria"
                once the ssh alias in nixos ssh.nix is deployed)
EOF
}

ROOT="$(git rev-parse --show-toplevel)" || {
  echo "error: not inside a git repo" >&2
  exit 1
}
cd "$ROOT"

assume_yes=0
explicit=()
for arg in "$@"; do
  case "$arg" in
  -y | --yes) assume_yes=1 ;;
  -h | --help)
    usage
    exit 0
    ;;
  *) explicit+=("$arg") ;;
  esac
done

# Build the file list: explicit args if given, else all working-tree changes
# (modified + untracked, honoring .gitignore). Skip anything that no longer
# exists on disk (e.g. deletions) so rsync doesn't error on a missing source.
files=()
if [ "${#explicit[@]}" -gt 0 ]; then
  for f in "${explicit[@]}"; do
    [ -e "$f" ] && files+=("$f")
  done
else
  while IFS= read -r f; do
    [ -n "$f" ] && [ -e "$f" ] && files+=("$f")
  done < <({ git diff --name-only; git ls-files --others --exclude-standard; } | sort -u)
fi

if [ "${#files[@]}" -eq 0 ]; then
  echo "Nothing to sync — working tree is clean (or given files don't exist)."
  exit 0
fi

echo "Will sync ${#files[@]} file(s) to ${REMOTE}:${DEST}"
printf '  %s\n' "${files[@]}"
echo
echo "── dry run ─────────────────────────────────────────────"
rsync -avR --dry-run "${files[@]}" "${REMOTE}:${DEST}"
echo "────────────────────────────────────────────────────────"

if [ "$assume_yes" -ne 1 ]; then
  printf 'Proceed with the real copy? [y/N] '
  read -r reply
  case "$reply" in
  [yY] | [yY][eE][sS]) ;;
  *)
    echo "Aborted."
    exit 1
    ;;
  esac
fi

rsync -avR "${files[@]}" "${REMOTE}:${DEST}"
echo "✔ Synced to ${REMOTE}:${DEST}"
