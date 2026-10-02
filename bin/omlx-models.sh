#!/bin/bash
# Download any oMLX model this host declares but does not have.
#
# The declaration is nix's services.omlxDeploy.models, written by activation to
# ~/.omlx/models.manifest as "<local-dir> <hf-repo>" lines. Models on disk but
# not declared are listed, never deleted: other tools may still use them.
#
#   omlx-models.sh           download what is missing
#   omlx-models.sh --check   report only; exit 1 if anything is missing
set -euo pipefail
IFS=$'\n\t'

MANIFEST="${OMLX_MODELS_MANIFEST:-$HOME/.omlx/models.manifest}"
MODELS="${OMLX_MODELS_DIR:-$HOME/Git/toolbox/dot/omlx/.omlx/models}"
HF=/opt/homebrew/opt/omlx/libexec/bin/hf
check=false
[ "${1:-}" = "--check" ] && check=true
[ "${1:-}" = "-h" ] && { sed -n '2,9p' "$0"; exit 0; }

[ -f "$MANIFEST" ] || { echo "no manifest at $MANIFEST; run the host's nix activation first" >&2; exit 2; }

missing=0
declared=()
while IFS=' ' read -r dir repo; do
  [ -n "$dir" ] || continue
  declared+=("$dir")
  if [ -f "$MODELS/$dir/config.json" ] && ! find "$MODELS/$dir" -name '*.incomplete' -print -quit | grep -q .; then
    echo "ok       $dir"
    continue
  fi
  missing=$((missing + 1))
  if $check; then
    echo "MISSING  $dir  ($repo)"
  else
    echo "fetching $dir  ($repo)"
    HF_XET_HIGH_PERFORMANCE=1 "$HF" download "$repo" --local-dir "$MODELS/$dir" >/dev/null
    echo "ok       $dir"
    missing=$((missing - 1))
  fi
done < "$MANIFEST"

for path in "$MODELS"/*; do
  name="$(basename "$path")"
  [ -L "$path" ] && continue
  printf '%s\n' "${declared[@]}" | grep -qxF "$name" || echo "extra    $name  (not declared; left alone)"
done

[ "$missing" -eq 0 ]
