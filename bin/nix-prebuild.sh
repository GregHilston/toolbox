#!/bin/bash
# Build a Mac's system at a commit and upload it to the Attic cache.
#
# `just dr` on dungeon or citadel pipes this to moria over ssh, so that host's
# deploy downloads instead of compiling. It runs from stdin, so moria's own
# checkout and its state don't matter: it uses a clone of its own.
# Usage: nix-prebuild.sh <commit> <host>
set -euo pipefail
IFS=$'\n\t'

sha=$1
host=$2
export PATH="/run/current-system/sw/bin:/nix/var/nix/profiles/default/bin:$PATH"
clone="$HOME/.cache/toolbox-prebuild"

[ -d "$clone" ] || git clone -q https://github.com/GregHilston/toolbox.git "$clone"
cd "$clone"
git fetch -q origin
git checkout -q --detach "$sha"
out=$(nix build --no-link --print-out-paths "./nixos#darwinConfigurations.$host.system")
attic=(attic)
# A moria deployed before #181 lacks it.
command -v attic >/dev/null || attic=(nix shell nixpkgs#attic-client -c attic)
# Off the tailnet, connecting hangs, not fails.
timeout 300 "${attic[@]}" push lab:darwin "$out" >/dev/null
echo "moria built and uploaded $host."
