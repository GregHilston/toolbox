#!/usr/bin/env bash
# Writes macOS battery metrics for the Prometheus node_exporter textfile collector.
# node_exporter has no battery collector on macOS, so this shells out to `pmset`
# and writes node_battery_percent / node_power_source into the textfile directory
# that node_exporter scrapes (--collector.textfile.directory, see the dungeon
# nix-darwin config). Run every 60s by a launchd user agent.
set -euo pipefail

TEXTFILE_DIR="${NODE_EXPORTER_TEXTFILE_DIR:-$HOME/.local/state/node_exporter}"
mkdir -p "$TEXTFILE_DIR"
OUT="$TEXTFILE_DIR/battery.prom"
TMP="$OUT.$$"

batt="$(pmset -g batt)"
# First percentage in the output, e.g. "85%;" -> 85
pct="$(printf '%s\n' "$batt" | grep -oE '[0-9]+%' | head -1 | tr -d '%')"
# Power source: "AC Power" -> 1, otherwise (Battery Power) -> 0
if printf '%s\n' "$batt" | grep -q "AC Power"; then on_ac=1; else on_ac=0; fi

{
  echo "# HELP node_battery_percent Battery charge percentage (from pmset)."
  echo "# TYPE node_battery_percent gauge"
  [ -n "${pct:-}" ] && echo "node_battery_percent ${pct}"
  echo "# HELP node_power_source On AC power (1) or battery (0), from pmset."
  echo "# TYPE node_power_source gauge"
  echo "node_power_source ${on_ac}"
} > "$TMP"
# Atomic replace so node_exporter never reads a half-written file.
mv -f "$TMP" "$OUT"
