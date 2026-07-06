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

With no target this wrapper shows ALL uncommitted changes (staged + unstaged),
like 'dhtml'. (Upstream difit defaults to the last commit; we default to '.').

Target-only keywords:
  difit                # all uncommitted changes (the default)
  difit .              # same — all uncommitted changes
  difit staged         # staged changes only
  difit working        # unstaged changes only
  difit @              # HEAD (the last commit)

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

# Default to '.' (all uncommitted changes) when no positional target is given —
# matches the 'dhtml' mental model. Upstream difit would otherwise show the last
# commit. A target is present unless there are no args, or the first is a flag.
if [[ $# -eq 0 || "$1" == -* ]]; then
  set -- . "$@"
fi

exec npx -y "difit@${DIFIT_VERSION}" "$@"
