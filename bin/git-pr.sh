#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Open the current branch as a GitHub-style PR diff in the browser (via difit).
# Compares HEAD against a base: an explicit first arg, else the repo's default
# branch (origin/HEAD -> origin/main, with fallbacks). Delegates to difit.sh so
# the pinned difit version lives in ONE place.

# Set GPR_MERGE_BASE=0 for a plain 2-dot diff instead of GitHub 3-dot semantics.
GPR_MERGE_BASE="${GPR_MERGE_BASE:-1}"

usage() {
  cat <<'EOF'
gpr — view the current branch as a GitHub-style PR diff (via difit)

Usage:
  gpr [base] [extra difit flags...]

  base   Branch/ref to compare against. Default: the repo's default branch
         (origin/HEAD -> origin/main, fallbacks main/master). Any argument
         starting with '-' is treated as a difit flag, not a base.

Examples:
  gpr                     # this branch vs auto-detected default (origin/main)
  gpr origin/develop      # vs a specific base
  gpr main --port 5000    # vs main, on a custom port
  gpr --no-open           # don't launch a browser
  GPR_MERGE_BASE=0 gpr    # plain 2-dot diff instead of 3-dot (merge-base)
EOF
}

case "${1:-}" in
  -h|--help) usage; exit 0 ;;
esac

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "gpr: not inside a git repository." >&2
  exit 1
fi

# Detect the base branch: prefer the remote's default (origin/HEAD), then fall back.
detect_base() {
  local ref candidate
  if ref="$(git symbolic-ref --quiet refs/remotes/origin/HEAD 2>/dev/null)"; then
    printf '%s\n' "${ref#refs/remotes/}"   # refs/remotes/origin/main -> origin/main
    return 0
  fi
  for candidate in origin/main origin/master main master; do
    if git rev-parse --verify --quiet "${candidate}^{commit}" >/dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

# First non-flag arg is the base; everything else passes through to difit.
base=""
if [[ $# -gt 0 && "$1" != -* ]]; then
  base="$1"; shift
fi

if [[ -z "$base" ]]; then
  if ! base="$(detect_base)"; then
    echo "gpr: could not detect a default branch (no origin/HEAD, main, or master)." >&2
    echo "     Pass one explicitly:  gpr <base-branch>" >&2
    exit 1
  fi
fi

# Refuse to compare a branch against itself.
current="$(git branch --show-current 2>/dev/null || true)"
if [[ -n "$current" && "$current" == "${base#origin/}" ]]; then
  echo "gpr: current branch '$current' is the base branch — nothing to compare." >&2
  echo "     For uncommitted changes use:  difit working" >&2
  exit 0
fi

# Ensure the base ref resolves to a commit.
if ! git rev-parse --verify --quiet "${base}^{commit}" >/dev/null 2>&1; then
  echo "gpr: base ref '$base' does not resolve to a commit." >&2
  echo "     You may need:  git fetch" >&2
  exit 1
fi

# GitHub 3-dot (merge-base) semantics by default; toggle off with GPR_MERGE_BASE=0.
mb_flag=()
if [[ "$GPR_MERGE_BASE" != "0" ]]; then
  mb_flag=(--merge-base)
fi

# Delegate to the pinned difit wrapper (single source of version truth).
# Grammar: difit <target> <base>  (diff is base -> target, so HEAD's work = additions)
exec difit.sh HEAD "$base" ${mb_flag[@]+"${mb_flag[@]}"} "$@"
