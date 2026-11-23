#!/usr/bin/env bash
# A repeated XO alert waits 1, 2, 4, then 8 h; a pass without it resets.
set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
eval "$(sed -n '/^fresh() {/,/^}/p; /^settle() {/,/^}/p' "$here/bin/control-loop.sh")"
once=0 raised=""
seen=$(mktemp -d)
trap 'rm -rf "$seen"' EXIT
key() { echo "$seen/a-$(printf %s "$1" | tr -d '0-9.' | cksum | cut -d' ' -f1)"; }
age() { python3 -c 'import os,sys,time; t=time.time()-int(sys.argv[2])*60; os.utime(sys.argv[1],(t,t))' "$(key x)" "$1"; }
check() { # check <want 0 fires|1 quiet> <want stored> <what>: one pass with the alert
  local got=0
  fresh x || got=1
  settle
  [ "$got" = "$1" ] || { echo "FAIL: $3: fresh gave $got, want $1"; exit 1; }
  [ "$(cat "$(key x)")" = "$2" ] || { echo "FAIL: $3: stored $(cat "$(key x)"), want $2"; exit 1; }
}
check 0 0 "first alert"
check 1 0 "same alert at once"
age 61;  check 0 1 "repeat after 1 h"
age 61;  check 1 1 "second repeat before 2 h"
age 121; check 0 2 "second repeat after 2 h"
age 241; check 0 3 "third repeat after 4 h"
age 481; check 0 3 "repeats stay at 8 h"
age 400; check 1 3 "quiet inside 8 h"
# 2026-11-23: main moved at 01:38, and a 4 h wait hid the next stall.
age 30; settle
[ "$(cat "$(key x)")" = r ] || { echo "FAIL: a pass without the alert kept $(cat "$(key x)")"; exit 1; }
check 1 r "the 1 h floor still holds after a reset"
age 61; check 0 0 "a new episode alerts after the floor"
age 61; check 0 1 "and backs off again"
echo ok
