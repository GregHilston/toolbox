#!/usr/bin/env bash
# Exclude large, regenerable directories from Time Machine (macOS only).
#
# Uses "sticky" exclusions (an xattr on the item) — no sudo needed for
# user-owned paths, and the exclusion follows the directory if it moves.
# /nix is a system path, so it needs sudo (last block).
#
# Sizes are reported at runtime rather than written into comments; the earlier
# version of this script carried hardcoded GB figures that were badly stale
# within months.
#
#   tm-exclude.sh --dry-run   report what would be excluded, change nothing
#   tm-exclude.sh             apply the exclusions
#
# To UNDO any of these later:  tmutil removeexclusion <path>

# Deliberately no `set -e`: one missing path or one tmutil failure should not
# abort the remaining exclusions. `-u` and `pipefail` still apply.
set -uo pipefail
IFS=$'\n\t'

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "tm-exclude.sh: macOS only (Time Machine)." >&2
  exit 1
fi

DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

exclude() {
  local path="$1" note="${2:-}" size
  if [[ ! -e "$path" ]]; then
    printf '  skip (missing)  %s\n' "$path"
    return
  fi

  size="$(du -sh "$path" 2>/dev/null | cut -f1)"
  size="${size:-?}"

  if tmutil isexcluded "$path" 2>/dev/null | grep -q '\[Excluded\]'; then
    printf '  already         %6s  %s\n' "$size" "$path"
    return
  fi

  if (( DRY_RUN )); then
    printf '  would exclude   %6s  %s%s\n' "$size" "$path" "${note:+  # $note}"
  elif tmutil addexclusion "$path" 2>/dev/null; then
    printf '  excluded        %6s  %s\n' "$size" "$path"
  else
    printf '  FAILED          %6s  %s\n' "$size" "$path"
  fi
}

echo "LLM model weights (all re-downloadable):"
exclude "$HOME/.lmstudio"                          "LM Studio models"
exclude "$HOME/Git/toolbox/dot/omlx/.omlx/models"  "oMLX models"
exclude "$HOME/Git/toolbox/dot/omlx/.omlx/cache"   "oMLX prefix cache"
exclude "$HOME/.omlx"                              "oMLX runtime KV cache"
exclude "$HOME/.ollama"                            "Ollama models"

echo
echo "Caches (regenerate on demand):"
exclude "$HOME/.cache"                             "HuggingFace + uv"
exclude "$HOME/Library/Caches"                     "Homebrew + app caches"

echo
echo "Container / VM disk images (regenerable — note the caveat below):"
exclude "$HOME/Library/Containers/com.docker.docker" "Docker Desktop"
exclude "$HOME/Virtual Machines.localized"           "VMware VMs, incl. mines"

echo
echo "Nix store (rebuildable from the flake; needs sudo):"
if [[ -d /nix ]]; then
  if (( DRY_RUN )); then
    printf '  would exclude   %6s  /nix\n' "$(du -sh /nix 2>/dev/null | cut -f1)"
  elif sudo tmutil addexclusion /nix; then
    echo "  excluded        /nix"
  fi
else
  echo "  skip (missing)  /nix"
fi

echo
if (( DRY_RUN )); then
  echo "Dry run — nothing changed. Re-run without --dry-run to apply."
else
  cat <<'EOF'
Done. Verify with:  tmutil isexcluded <path>

Caveat: excluding the Docker container directory also excludes any *container
volumes* living there — those are not backed up. Fine for rebuildable dev
containers, not for a database you care about.

Pick up the exclusions by restarting the current backup:
  tmutil stopbackup ; tmutil startbackup
EOF
fi
