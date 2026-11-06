#!/bin/bash
# Build a Mac's system at a pushed commit and upload it to the Attic cache.
# Usage: nix-prebuild.sh <commit> <host>
{
  set -euo pipefail
  IFS=$'\n\t'
  export PATH="/run/current-system/sw/bin:/nix/var/nix/profiles/default/bin:$PATH"
  # A flake ref, not a clone: concurrent runs can't collide.
  out=$(nix build --no-link --print-out-paths \
    "github:GregHilston/toolbox/$1?dir=nixos#darwinConfigurations.$2.system")
  # Off the tailnet, connecting hangs, not fails.
  timeout 300 nix shell nixpkgs#attic-client -c attic push lab:darwin "$out" >/dev/null
  echo "moria built and uploaded $2."
  exit
}
