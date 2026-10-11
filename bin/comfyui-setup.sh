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
REF="${COMFYUI_REF:-v0.39.2}"
# Pinned because nightlies are deleted upstream; torchvision must match torch.
TORCH=(torch==2.14.1 torchvision==0.29.1)
TRIES="${COMFYUI_FETCH_TRIES:-20}"
AGENT="gui/$(id -u)/org.nixos.comfyui"

# Folder under models/, then URL. Base and distilled both: the bundled
# "Flux.2 [Klein] 4B" template opens on base, and distilled is the 4-step one.
MODELS=(
  "diffusion_models https://huggingface.co/Comfy-Org/flux2-klein/resolve/main/split_files/diffusion_models/flux-2-klein-4b.safetensors"
  "diffusion_models https://huggingface.co/Comfy-Org/flux2-klein/resolve/main/split_files/diffusion_models/flux-2-klein-base-4b.safetensors"
  "text_encoders https://huggingface.co/Comfy-Org/flux2-klein/resolve/main/split_files/text_encoders/qwen_3_4b.safetensors"
  "vae https://huggingface.co/Comfy-Org/flux2-dev/resolve/main/split_files/vae/flux2-vae.safetensors"
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
printf "✓ venv (%s %s)\n" "${TORCH[@]}"

# Written once: the Manager edits this file itself. The server listens on a
# tailnet address, which the Manager calls non-local and refuses installs from
# unless network_mode is personal_cloud. use_uv because a uv venv has no pip.
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

remote_size() {  # <url>  prints the Content-Length after redirects
  curl -sfIL "$1" | tr -d '\r' | awk 'tolower($1) == "content-length:" { n = $2 } END { print n }'
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
  tries=0
  # Resume until the size matches: Hugging Face's CDN stalls mid-file on a weak
  # link, and --speed-limit turns a stall into an exit we can retry.
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
