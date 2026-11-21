#!/usr/bin/env bash
# A due item fires once, at its time, and not before.
set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
CONTROL_LOOP_DIR=$(mktemp -d)
export CONTROL_LOOP_DIR
f=$CONTROL_LOOP_DIR/loser-picks/due
mkdir -p "$(dirname "$f")"
now=$(date +%s)
printf '%s %s\n' $((now - 60)) "check load" $((now + 3600)) "measure throughput" > "$f"
got=$("$here/bin/xo-due" pop "$f")
[ "$got" = "check load" ] || { echo "FAIL: popped '$got'"; exit 1; }
[ -z "$("$here/bin/xo-due" pop "$f")" ] || { echo "FAIL: fired twice"; exit 1; }
grep -q "measure throughput" "$f" || { echo "FAIL: future item lost"; exit 1; }
"$here/bin/xo-due" add 00:00 "midnight" > /dev/null
[ "$(awk '$2=="midnight"{print $1}' "$f")" -gt "$now" ] || { echo "FAIL: a past time is not tomorrow"; exit 1; }
grep -q 'xo-due" pop' "$here/bin/control-loop.sh" || { echo "FAIL: the XO never pops due items"; exit 1; }
echo ok
