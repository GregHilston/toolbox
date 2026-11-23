#!/usr/bin/env bash
# One host busy while the other idles raises an alert.
set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
eval "$(sed -n '/^imbalance() {/,/^}/p' "$here/bin/control-loop.sh")"
imbalance 71 6 || { echo "FAIL: moria 71, foundation 6 is quiet"; exit 1; }
imbalance 5 40 || { echo "FAIL: the other way round is quiet"; exit 1; }
! imbalance 30 20 || { echo "FAIL: both busy alerts"; exit 1; }
! imbalance 6 3 || { echo "FAIL: both idle alerts"; exit 1; }
! imbalance 71 "" || { echo "FAIL: an unreachable host alerts"; exit 1; }
grep -q 'imbalance "\$near" "\$fl"' "$here/bin/control-loop.sh" || { echo "FAIL: the loop never checks"; exit 1; }
echo ok
