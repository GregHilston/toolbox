#!/usr/bin/env bash
# An idle train lane with approved work alerts.
set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
eval "$(sed -n '/^lane_idle() {/,/^}/p' "$here/bin/control-loop.sh")"
lane_idle 29 40 || { echo "FAIL: 29 min idle, 40 approved is quiet"; exit 1; }
! lane_idle 10 40 || { echo "FAIL: 10 min idle alerts"; exit 1; }
! lane_idle 60 0 || { echo "FAIL: nothing approved alerts"; exit 1; }
! lane_idle "" 40 || { echo "FAIL: a running train alerts"; exit 1; }
grep -q 'lane_idle "\$idle" "\$approved"' "$here/bin/control-loop.sh" || { echo "FAIL: the loop never checks"; exit 1; }
echo ok
