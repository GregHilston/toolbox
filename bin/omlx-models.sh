#!/bin/bash
# Download any oMLX model this host declares but does not have.
#
# The declaration is nix's services.omlxDeploy (lightModel plus models), written
# by activation to ~/.omlx/models.manifest as "<local-dir> <hf-repo>" lines.
# Models on disk but not declared are listed, never deleted: other tools may
# still use them. A model counts as present only when every weight shard named
# in its index is on disk, since an interrupted download leaves config.json.
#
#   omlx-models.sh           download what is missing
#   omlx-models.sh --check   report only; exit 1 if anything is missing
set -euo pipefail
IFS=$'\n\t'

MANIFEST="${OMLX_MODELS_MANIFEST:-$HOME/.omlx/models.manifest}"
MODELS="${OMLX_MODELS_DIR:-$HOME/Git/toolbox/dot/omlx/.omlx/models}"
HF=/opt/homebrew/opt/omlx/libexec/bin/hf
check=false
case "${1:-}" in
  --check) check=true ;;
  -h | --help) sed -n '2,11p' "$0"; exit 0 ;;
esac

[ -f "$MANIFEST" ] || { echo "no manifest at $MANIFEST; run the host's nix activation first" >&2; exit 2; }

complete() {  # <dir>
  local d="$1" index="$1/model.safetensors.index.json"
  [ -f "$d/config.json" ] || return 1
  find "$d" -name '*.incomplete' -print -quit | grep -q . && return 1
  if [ -f "$index" ]; then
    python3 -c 'import json,os,sys; d=sys.argv[1]; m=json.load(open(sys.argv[2]))["weight_map"]; sys.exit(any(not os.path.exists(os.path.join(d,f)) for f in set(m.values())))' "$d" "$index"
  else
    [ -f "$d/model.safetensors" ]
  fi
}

failed=0
declared=()
while IFS=' ' read -r dir repo; do
  [ -n "$dir" ] || continue
  declared+=("$dir")
  if complete "$MODELS/$dir"; then
    echo "ok       $dir"
  elif $check; then
    echo "MISSING  $dir  ($repo)"
    failed=$((failed + 1))
  elif [ ! -x "$HF" ]; then
    echo "MISSING  $dir  ($repo): no hf at $HF; is oMLX installed?" >&2
    failed=$((failed + 1))
  elif echo "fetching $dir  ($repo)" && HF_XET_HIGH_PERFORMANCE=1 "$HF" download "$repo" --local-dir "$MODELS/$dir" --quiet >/dev/null && complete "$MODELS/$dir"; then
    echo "ok       $dir"
  else
    echo "FAILED   $dir  ($repo)" >&2
    failed=$((failed + 1))
  fi
done < "$MANIFEST"

for path in "$MODELS"/*; do
  [ -e "$path" ] && [ ! -L "$path" ] || continue
  name="$(basename "$path")"
  printf '%s\n' "${declared[@]}" | grep -qxF "$name" || echo "extra    $name  (not declared; left alone)"
done

[ "$failed" -eq 0 ]
