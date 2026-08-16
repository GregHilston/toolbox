#!/bin/bash
# Audit a benchmark window for foreign traffic on the shared oMLX server.
#
# Why this exists: roger's digest job once hammered gpt-oss-120b on the same
# server during a benchmark and silently depressed one model's measurement by
# ~20%. Nothing in the benchmark output hinted at it.
#
# This script MUST fail closed. A false "CLEAN" is worse than no check at all,
# because it launders a contaminated run as verified. Every parse failure below
# is therefore a hard exit, not a warning.
#
# Usage: contention_audit.sh <window-file> <expected-model-id>
#   <window-file>      two lines, as written by the bench drivers:
#                        START 2026-08-15 17:25:53
#                        END 2026-08-15 17:35:39
#   <expected-model-id> EXACT model id under test, e.g. Qwen3.8-27B-4bit.
#                       Anything else served in the window is foreign --
#                       including a different Qwen, which is exactly the
#                       engine-pool-residency confound.
set -u

W="${1:-}"
EXPECT="${2:-}"
LOG="${OMLX_LOG:-$HOME/Library/Logs/omlx.log}"

die () { echo "FATAL: $*" >&2; exit 2; }

[ -n "$W" ] && [ -n "$EXPECT" ] || die "usage: $(basename "$0") <window-file> <expected-model-id>"
[ -r "$W" ]   || die "window file not readable: $W"
[ -r "$LOG" ] || die "oMLX log not readable: $LOG (set OMLX_LOG to override)"

# Time is the LAST field on each line, so this survives both
# "START 17:25:53" and "START 2026-08-15 17:25:53".
START=$(awk '/^START/{print $NF}' "$W")
END=$(awk '/^END/{print $NF}'   "$W")

[ -n "$START" ] || die "could not parse START from $W (expected a line beginning 'START')"
[ -n "$END" ]   || die "could not parse END from $W (expected a line beginning 'END'). \
An unfinished run has no END - the benchmark may still be running."

echo "window: $START -> $END   (expected model: $EXPECT)"

# Substring-match the model id, then exclude exact matches for the expected one.
# awk compares HH:MM:SS lexically, which is correct for zero-padded times within a day.
foreign=$(grep "Chat completion: model=" "$LOG" \
  | awk -v s="$START" -v e="$END" '{t=substr($2,1,8)} t>=s && t<=e' \
  | sed 's/.*model=\([^,]*\),.*/\1/' \
  | grep -vxF "$EXPECT" || true)

total=$(grep "Chat completion: model=" "$LOG" \
  | awk -v s="$START" -v e="$END" '{t=substr($2,1,8)} t>=s && t<=e' | wc -l | tr -d ' ')

if [ "$total" -eq 0 ]; then
  die "no requests at all in window $START-$END. Either the window is wrong or the \
log rotated - refusing to report CLEAN on an empty window."
fi

n=$(printf '%s' "$foreign" | grep -c . || true)
if [ "$n" -eq 0 ]; then
  echo "  CLEAN - $total requests in window, all $EXPECT"
  exit 0
fi
echo "  !! $n of $total requests were FOREIGN - results are suspect:"
printf '%s\n' "$foreign" | sort | uniq -c | sed 's/^/    /'
exit 1
