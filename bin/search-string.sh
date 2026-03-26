#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Recursively search for a string in the current directory (uses ripgrep if available)

if hash rg 2>/dev/null; then
  rg "${1}"
else
  echo "ripgrep not installed, falling back on grep"
  grep -niro "${1}" "$PWD"
fi
