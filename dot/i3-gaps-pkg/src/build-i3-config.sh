#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG_DIR="$(dirname "$SCRIPT_DIR")"

host=$(hostname)
if [[ ! -f "$SCRIPT_DIR/config-$host" ]]; then
    echo "Error: no config fragment found for host '$host'"
    echo "Available hosts:"
    ls "$SCRIPT_DIR"/config-* | sed 's/.*config-/  /'
    exit 1
fi

cat "$SCRIPT_DIR/config-base" \
    "$SCRIPT_DIR/config-$host" > "$PKG_DIR/.config/i3/config"

echo "Built i3-gaps config for $host"
