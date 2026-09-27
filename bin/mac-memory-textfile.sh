#!/usr/bin/env bash
# Writes macOS memory-pressure metrics for the node_exporter textfile collector.
# node_exporter's darwin "swapped_in" counter is really page-ins (file reads, such as
# oMLX mmapping model weights), so it reads high even when nothing swaps. The true
# swap traffic comes from vm_stat, and the kernel's own verdict from sysctl. Also counts
# oMLX's prefill throttling, its first reaction to a full machine. Run every 60s.
set -euo pipefail

TEXTFILE_DIR="${NODE_EXPORTER_TEXTFILE_DIR:-$HOME/.local/state/node_exporter}"
OMLX_LOG="${OMLX_LOG:-$HOME/Library/Logs/omlx.log}"
mkdir -p "$TEXTFILE_DIR"
OUT="$TEXTFILE_DIR/memory.prom"
TMP="$OUT.$$"

vm="$(vm_stat)"
page="$(printf '%s\n' "$vm" | sed -n 's/.*page size of \([0-9]*\) bytes.*/\1/p')"
count() { printf '%s\n' "$vm" | awk -v k="$1" '$0 ~ "^"k":" {gsub(/\./, "", $NF); print $NF}'; }
swapins=$(( $(count Swapins) * page ))
swapouts=$(( $(count Swapouts) * page ))
# 1 normal, 2 warning, 4 critical.
level="$(sysctl -n kern.memorystatus_vm_pressure_level)"
free_pct="$(memory_pressure -Q 2>/dev/null | sed -n 's/.*percentage: \([0-9]*\)%.*/\1/p')"
throttled=0
[ -f "$OMLX_LOG" ] && throttled="$(grep -c adaptive_prefill_throttle "$OMLX_LOG" || true)"

{
  echo "# HELP mac_memory_pressure_level Kernel memory pressure: 1 normal, 2 warning, 4 critical."
  echo "# TYPE mac_memory_pressure_level gauge"
  echo "mac_memory_pressure_level ${level}"
  echo "# HELP mac_memory_swapins_bytes_total Bytes swapped in since boot (vm_stat Swapins)."
  echo "# TYPE mac_memory_swapins_bytes_total counter"
  echo "mac_memory_swapins_bytes_total ${swapins}"
  echo "# HELP mac_memory_swapouts_bytes_total Bytes swapped out since boot (vm_stat Swapouts)."
  echo "# TYPE mac_memory_swapouts_bytes_total counter"
  echo "mac_memory_swapouts_bytes_total ${swapouts}"
  [ -n "$free_pct" ] && {
    echo "# HELP mac_memory_free_percent System-wide free memory percentage (memory_pressure)."
    echo "# TYPE mac_memory_free_percent gauge"
    echo "mac_memory_free_percent ${free_pct}"
  }
  echo "# HELP omlx_prefill_throttled_total Prefill throttle lines in oMLX's log; resets when the log does."
  echo "# TYPE omlx_prefill_throttled_total counter"
  echo "omlx_prefill_throttled_total ${throttled}"
} > "$TMP"
mv -f "$TMP" "$OUT"
