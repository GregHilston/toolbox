#!/bin/bash
# Install or upgrade Strata for the launchd agent in nixos/modules/darwin/strata.nix.
#
# Checks Strata out at a pinned commit into $STRATA_DIR, builds its Metal engine,
# downloads the Qwen3.8-Flash-Next pack its wizard picks (IQ3_S on 128 GB, ~86 GB
# into ../Strata-data), adds our serving defaults to the config, then restarts
# the agent. Safe to re-run: it is also the upgrade path. Why Strata, and how it
# measured: docs/local-llm-benchmarks.md (2026-10-26).
#
#   strata-setup.sh     (or `just strata-setup` from nixos/)
set -euo pipefail
IFS=$'\n\t'

DIR="${STRATA_DIR:-$HOME/Git/strata}"
# v0.2.15. A release commit, not a branch: releases land daily, and 2.x broke
# LAN auth. How to move it: docs/strata.md, Upgrading.
REF="${STRATA_REF:-c77572806996349b49995e4f98d41b5294d36a21}"
AGENT="gui/$(id -u)/org.nixos.strata"

case "${1:-}" in
  -h | --help) sed -n '2,10p' "$0"; exit 0 ;;
esac

export GIT_TERMINAL_PROMPT=0
if [ -d "$DIR/.git" ]; then
  git -C "$DIR" -c credential.helper= fetch --quiet origin
else
  git -c credential.helper= clone --quiet https://github.com/Niko1221/Strata.git "$DIR"
fi
before=$(git -C "$DIR" rev-parse HEAD)
git -C "$DIR" checkout --quiet --detach "$REF"
echo "✓ Strata $(git -C "$DIR" rev-parse --short HEAD) in $DIR"

build=()
[ "$before" = "$(git -C "$DIR" rev-parse HEAD)" ] || build=(--build)
# Apple's clang: nix-darwin's cc carries an SDK too old for the Metal build.
(cd "$DIR" && PATH=/usr/bin:/bin:/usr/sbin:/sbin CC=/usr/bin/clang CXX=/usr/bin/clang++ \
  SDKROOT="$(xcrun --sdk macosx --show-sdk-path)" \
  ./setup.sh --yes --no-start --no-browser --vision no ${build[@]+"${build[@]}"})

# Setup rewrites the config on every run, so these go back on after it.
config=$(ls "$DIR"/strata-*.json | head -1)
# fp16 Metal decode (v0.2.13 default) changes answers.
jq '. + {lazy_load: true, idle_unload_s: 1800, reasoning_effort: "medium",
         reasoning_budget_tokens: 16384}
        | .env += {STRATA_METAL_F16: "0"}
        | .args |= (index("--max-context") as $i | .[$i + 1] = "262144")' "$config" >"$config.tmp"
mv "$config.tmp" "$config"
ln -sfn "$config" "$DIR/strata.json"
echo "✓ config $config"

launchctl kickstart -k "$AGENT" 2>/dev/null && echo "✓ restarted $AGENT" \
  || echo "! $AGENT is not loaded yet: run 'just dr moria'"
