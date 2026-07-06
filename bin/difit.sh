#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Version-pinned wrapper around difit (browser-based git diff / PR viewer).
# difit is NOT in nixpkgs, so we run it via npx at an exact pinned version.
# Bump the tool by editing DIFIT_VERSION below (single source of truth).

DIFIT_VERSION="${DIFIT_VERSION:-5.0.6}"

usage() {
  cat <<EOF
difit — browser-based git diff / PR viewer (pinned to difit@${DIFIT_VERSION} via npx)

Usage:
  difit [target] [base] [flags]

Target-only keywords:
  difit working        # unstaged + staged uncommitted changes
  difit staged         # staged changes only
  difit .              # all uncommitted changes
  difit @              # HEAD (last commit)

Branch / PR comparison (target first, base second; diff is base -> target,
so the target's work shows as additions):
  difit HEAD main               # commits on this branch vs main
  difit HEAD main --merge-base  # GitHub-style 3-dot diff (vs merge-base)

Useful flags: --no-open  --port <n>  --host <h>  --merge-base
              --include-untracked  --context <n>  --pr <url>

See also: 'gpr' (git-pr.sh) auto-detects the base branch for PR review.
Bump the pinned version by editing DIFIT_VERSION in this script, or override
per-run:  DIFIT_VERSION=5.1.0 difit ...
EOF
}

case "${1:-}" in
  -h|--help) usage; exit 0 ;;
esac

if ! command -v npx >/dev/null 2>&1; then
  cat >&2 <<'EOF'
difit: 'npx' not found — difit needs a Node.js runtime.
Available only on Mac hosts (citadel via volta; dungeon/moria via Homebrew node).
NixOS hosts have node only inside per-project dev shells.
EOF
  exit 127
fi

exec npx -y "difit@${DIFIT_VERSION}" "$@"
