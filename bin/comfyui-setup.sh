#!/bin/bash
# Install or upgrade ComfyUI for the launchd agent in nixos/modules/darwin/comfyui.nix.
#
# Clones ComfyUI at a pinned release into $COMFYUI_DIR, builds its uv venv with
# a pinned PyTorch, enables ComfyUI-Manager, downloads the FLUX.2 klein 4B
# model files, then restarts the agent. Safe to re-run: it is also the upgrade
# path, and a model file already at its full size is never fetched again.
#
#   comfyui-setup.sh     (or `just comfyui-setup` from nixos/)
set -euo pipefail
IFS=$'\n\t'

DIR="${COMFYUI_DIR:-$HOME/ComfyUI}"
REF="${COMFYUI_REF:-v0.39.2}" # a release tag
# Stable: nightlies are deleted. Manager needs all three.
TORCH=(torch==2.14.1 torchvision==0.29.1 torchaudio==2.11.0)
TRIES="${COMFYUI_FETCH_TRIES:-20}"
AGENT="gui/$(id -u)/org.nixos.comfyui"

# Folder under models/, then URL, pinned to a commit so a resume never splices
# two versions. Base too: the bundled klein template opens on it.
KLEIN=https://huggingface.co/Comfy-Org/vae-text-encorder-for-flux-klein-4b/resolve/5f526678002e43af5551dadb73ce2e8c91b43afe/split_files
FLUX2=https://huggingface.co/Comfy-Org/flux2-dev/resolve/ed33133cd56476eac818c0943b6f9419b3e4a3a1/split_files
MODELS=(
  "diffusion_models $KLEIN/diffusion_models/flux-2-klein-4b.safetensors"
  "diffusion_models $KLEIN/diffusion_models/flux-2-klein-base-4b.safetensors"
  "text_encoders $KLEIN/text_encoders/qwen_3_4b.safetensors"
  "vae $FLUX2/vae/flux2-vae.safetensors"
)
if [ -n "${COMFYUI_MODELS:-}" ]; then
  read -r -d '' -a MODELS <<<"$COMFYUI_MODELS" || true
fi

case "${1:-}" in
  -h | --help) sed -n '2,9p' "$0"; exit 0 ;;
esac

# A credential helper that prompts hangs a non-interactive run (seen over ssh).
export GIT_TERMINAL_PROMPT=0
if [ -d "$DIR/.git" ]; then
  git -C "$DIR" -c credential.helper= fetch --quiet --tags origin
else
  git -c credential.helper= clone --quiet https://github.com/Comfy-Org/ComfyUI.git "$DIR"
fi
git -C "$DIR" checkout --quiet "$REF"
echo "✓ ComfyUI $REF in $DIR"

[ -x "$DIR/.venv/bin/python" ] || uv venv --quiet --python 3.12 "$DIR/.venv"
UV_HTTP_TIMEOUT=600 uv pip install --quiet --python "$DIR/.venv/bin/python" "${TORCH[@]}" \
  -r "$DIR/requirements.txt" -r "$DIR/manager_requirements.txt"
printf "✓ venv:"; printf " %s" "${TORCH[@]}"; echo

# Written once; the Manager edits it after. Why: nixos/CLAUDE.md.
manager_ini="$DIR/user/__manager/config.ini"
if [ ! -f "$manager_ini" ]; then
  mkdir -p "$(dirname "$manager_ini")"
  printf '[default]\nuse_uv = True\nnetwork_mode = personal_cloud\n' >"$manager_ini"
  echo "✓ ComfyUI-Manager config"
fi

# wc, not stat: moria's PATH puts GNU stat first, where -f means filesystem.
local_size() {  # <file>
  if [ -f "$1" ]; then wc -c <"$1" | tr -d ' '; else echo 0; fi
}

remote_size() {  # <url>  the final response's Content-Length, or nothing
  { curl -sfIL "$1" || true; } | tr -d '\r' |
    awk '/^HTTP\// { n = "" } tolower($1) == "content-length:" { n = $2 } END { print n }'
}

failed=0
for entry in "${MODELS[@]}"; do
  folder="${entry%% *}" url="${entry#* }"
  out="$DIR/models/$folder/${url##*/}"
  mkdir -p "$(dirname "$out")"
  size=$(remote_size "$url")
  if [ -z "$size" ]; then
    echo "✗ cannot size $url" >&2; failed=1; continue
  fi
  # Resuming past the end never shrinks a file.
  [ "$(local_size "$out")" -le "$size" ] || rm -f "$out"
  tries=0
  # Hugging Face stalls mid-file; resume until complete.
  while [ "$(local_size "$out")" != "$size" ]; do
    if [ "$tries" -ge "$TRIES" ]; then
      echo "✗ gave up on ${out##*/} after $TRIES tries" >&2; failed=1; continue 2
    fi
    tries=$((tries + 1))
    curl -sfL --speed-limit 500000 --speed-time 30 -C - -o "$out" "$url" || sleep 2
  done
  echo "✓ ${out##*/}"
done

if launchctl print "$AGENT" >/dev/null 2>&1; then
  launchctl kickstart -k "$AGENT"
  echo "✓ restarted $AGENT"
else
  echo "  $AGENT is not loaded; enable custom.services.comfyui and run 'just dr <host>'."
fi
exit "$failed"
