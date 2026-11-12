#!/usr/bin/env bash
# Writes macOS memory-pressure metrics for the node_exporter textfile collector.
# node_exporter's darwin "swapped_in" counter is really page-ins (file reads, such as
# oMLX mmapping model weights), so it reads high even when nothing swaps. The true
# swap traffic comes from vm_stat, and the kernel's own verdict from sysctl. Also counts
# oMLX's prefill throttling, its first reaction to a full machine, and each app's
# footprint. Run every 60s.
set -euo pipefail

TEXTFILE_DIR="${NODE_EXPORTER_TEXTFILE_DIR:-$HOME/.local/state/node_exporter}"
OMLX_LOG="${OMLX_LOG:-$HOME/Library/Logs/omlx.log}"
mkdir -p "$TEXTFILE_DIR"
OUT="$TEXTFILE_DIR/memory.prom"
TMP="$OUT.$$"
trap 'rm -f "$TMP"' EXIT

vm="$(vm_stat)"
page="$(printf '%s\n' "$vm" | sed -n 's/.*page size of \([0-9]*\) bytes.*/\1/p')"
count() { printf '%s\n' "$vm" | awk -v k="$1" '$0 ~ "^"k":" {gsub(/\./, "", $NF); print $NF}'; }
swapins=$(( $(count Swapins) * page ))
swapouts=$(( $(count Swapouts) * page ))
level="$(sysctl -n kern.memorystatus_vm_pressure_level)"
free_pct="$(memory_pressure -Q 2>/dev/null | sed -n 's/.*percentage: \([0-9]*\)%.*/\1/p' || true)"
throttled=0
[ -f "$OMLX_LOG" ] && throttled="$(grep -c adaptive_prefill_throttle "$OMLX_LOG" || true)"

# top's MEM is the phys footprint: it counts Metal buffers and the
# OrbStack VM, which RSS misses. Grouped by app, so a pid's restart keeps its series.
by_app="$(awk '
  NR == FNR {
    pid = $1; sub(/^ *[0-9]+ /, ""); c = $0
    if (c ~ /\/claude\/versions\//) g = "claude"
    else if (match(c, /[^\/]+\.app\//)) g = substr(c, RSTART, RLENGTH - 5)
    else { n = split(c, p, "/"); g = p[n] }
    gsub(/["\\]/, "", g); app[pid] = g; next
  }
  $1 in app {
    m = $2; sub(/[+-]$/, "", m); u = substr(m, length(m)); v = substr(m, 1, length(m) - 1)
    b[app[$1]] += v * (u == "G" ? 1073741824 : u == "M" ? 1048576 : u == "K" ? 1024 : 1)
  }
  END {
    if (!length(b)) exit
    for (g in b) if (b[g] >= 52428800) printf "mac_process_memory_bytes{app=\"%s\"} %.0f\n", g, b[g]; else rest += b[g]
    printf "mac_process_memory_bytes{app=\"other\"} %.0f\n", rest
  }' <(ps -axo pid=,comm= 2>/dev/null) <(top -l 1 -stats pid,mem 2>/dev/null) || true)"

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
  [ -n "$by_app" ] && {
    echo "# HELP mac_process_memory_bytes Phys footprint (top MEM) summed per app; apps under 50 MB are other."
    echo "# TYPE mac_process_memory_bytes gauge"
    printf '%s\n' "$by_app"
  }
} > "$TMP"
mv -f "$TMP" "$OUT"
