#!/bin/bash
# Audit a benchmark window for foreign traffic on the shared oMLX server.
# Usage: contention_audit.sh <window-file> <expected-model-substring>
# Prints any Chat completion served in the window whose model does NOT match.
set -u
W="${1:-final_window.txt}"
EXPECT="${2:-Qwen3.}"
LOG="$HOME/Library/Logs/omlx.log"

START=$(awk '/START/{print $3}' "$W")
END=$(awk '/END/{print $3}' "$W")
echo "window: $START -> $END   (expecting only models matching '$EXPECT')"

grep "Chat completion: model=" "$LOG" \
  | awk -v s="$START" -v e="$END" '{t=substr($2,1,8)} t>=s && t<=e' \
  | grep -v "model=$EXPECT" \
  | sed 's/.*model=/  FOREIGN: /' | sort | uniq -c

n=$(grep "Chat completion: model=" "$LOG" \
      | awk -v s="$START" -v e="$END" '{t=substr($2,1,8)} t>=s && t<=e' \
      | grep -vc "model=$EXPECT")
if [ "$n" -eq 0 ]; then echo "  CLEAN - no foreign requests in window"; else echo "  !! $n foreign requests - results suspect"; fi
