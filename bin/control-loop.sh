#!/bin/bash
# control-loop.sh [--wake hc:T|herdr:P] [--name N] [--watch FILE] [--once] [--send TEXT] [seconds]
# A control loop: no LLM, checks on a timer, wakes its target by typing "XO: ..." into its pane.
# This one is the commander's XO (docs/commander.md); state is ~/.cache/control-loop/<name>/.
# Env: XO_HOST (moriats), XO_TERM (t17), XO_REPO (loser-picks), XO_FAR (foundationts).
set -euo pipefail
IFS=$'\n\t'

host=${XO_HOST:-moriats} term=${XO_TERM:-t17} repo=${XO_REPO:-loser-picks} far=${XO_FAR:-foundationts}
slug=GregHilston/$repo
args=("$@")
wake="" name=$repo watch="" once=0 send="" interval=600
while [ $# -gt 0 ]; do
  case $1 in
    --wake) wake=$2; shift 2 ;;
    --name) name=$2; shift 2 ;;
    --watch) watch=$2; shift 2 ;;
    --once) once=1; shift ;;
    --send) send=$2; shift 2 ;;
    -h | --help) sed -n 2,6p "$0"; exit 0 ;;
    *) interval=$1; shift ;;
  esac
done
[ "$once" = 1 ] || [ -n "$wake" ] || { echo "control-loop: --wake is required unless --once" >&2; exit 2; }
dir=${CONTROL_LOOP_DIR:-$HOME/.cache/control-loop}/$name
seen=$dir/seen
watch=${watch:-$dir/closes}
mkdir -p "$seen"

# Fd 9 holds the lock; the python wrapper execs this script so the pid stays the holder's.
if [ "$once" = 0 ] && [ -z "$send" ] && [ -z "${CL_LOCKED-}" ]; then
  CL_LOCKED=1 exec python3 -c '
import fcntl, os, sys
fd = os.open(sys.argv[1], os.O_CREAT | os.O_RDWR)
try:
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except OSError:
    sys.exit("control-loop: already running for this target, pid " + os.pread(fd, 20, 0).decode().strip())
os.ftruncate(fd, 0)
os.write(fd, str(os.getpid()).encode())
os.dup2(fd, 9)
os.close(fd)
os.set_inheritable(9, True)
os.execvp(sys.argv[2], sys.argv[2:])
' "$dir/lock" bash "$0" "${args[@]}"
fi

CL_POLL=${CL_POLL:-5} CL_SETTLE=${CL_SETTLE:-3} CL_IDLE_TIMEOUT=${CL_IDLE_TIMEOUT:-300} CL_ROLL_TIMEOUT=${CL_ROLL_TIMEOUT:-1500}
kind=${wake%%:*} id=${wake#*:}
pane=$id
[ "$kind" = hc ] && pane=$wake

once() { # once <key>: true the first time a key is seen
  [ "$once" = 1 ] && return 0
  [ -e "$seen/$1" ] && return 1
  : > "$seen/$1"
}
fresh() { # fresh <alert>: true unless the same alert fired in the last hour
  [ "$once" = 1 ] && return 0
  local k="$seen/a-$(printf %s "$1" | tr -d '0-9.' | cksum | cut -d' ' -f1)"
  [ -z "$(find "$k" -mmin -60 2>/dev/null)" ] || return 1
  : > "$k"
}

# until_false <timeout> <cmd...>: poll while the command succeeds, up to the timeout.
until_false() {
  local limit=$1 n i
  shift
  n=$(awk "BEGIN{print int($limit/$CL_POLL)+1}")
  for ((i = 0; i < n; i++)); do
    "$@" || return 0
    sleep "$CL_POLL"
  done
}
roll_queued() {
  PYTHONPATH=$(dirname "$0") python3 -c '
import json, sys, claude_shift
try:
    s = json.loads(claude_shift.state_path(sys.argv[1]).read_text())
except Exception:
    sys.exit(1)
sys.exit(0 if s.get("roll_id") or s.get("worker_pid") else 1)
' "$pane"
}
working() {
  local s
  if [ "$kind" = hc ]; then
    s=$(hc get "$id" --json 2>/dev/null | python3 -c 'import json,sys; print((json.load(sys.stdin).get("status") or {}).get("state",""))' || true)
    [ "$s" = working ]
  else
    s=$(herdr agent get "$id" 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["agent"]["agent_status"])' || true)
    [ "$s" != idle ] && [ "$s" != done ]
  fi
}
type_in() { if [ "$kind" = hc ]; then hc send "$id" "$1" --json >/dev/null; else herdr agent prompt "$id" "$1" >/dev/null; fi; }
screen() { if [ "$kind" = hc ]; then hc read "$id"; else herdr agent read "$id"; fi 2>/dev/null; }

deliver() { # a send to a working terminal can vanish, so read the screen back
  local text=$1
  until_false "$CL_ROLL_TIMEOUT" roll_queued
  until_false "$CL_IDLE_TIMEOUT" working
  type_in "$text"
  sleep "$CL_SETTLE"
  screen | grep -qF -- "${text:0:30}" || type_in "$text"
}

if [ -n "$send" ]; then deliver "$send"; exit 0; fi

last_main="" quiet_since=$(date +%s)
if [ -r "$dir/main" ]; then IFS=" " read -r last_main quiet_since < "$dir/main"; fi

while :; do
  out=$(timeout 60 ssh -o ConnectTimeout=10 "$host" "
    load=\$(uptime | sed -E 's/.*load averages?: *([0-9.]+).*/\1/')
    hc get $term --json 2>/dev/null | python3 -c '
import json,sys,time
d=json.load(sys.stdin); s=d.get(\"status\") or {}
load=float(sys.argv[1])
if d.get(\"state\")!=\"live\": print(\"XO $repo: terminal\",d.get(\"state\"))
elif s.get(\"state\")==\"blocked\": print(\"XO $repo: blocked:\",(s.get(\"msg\") or \"\")[:200])
elif s.get(\"app\")!=\"claude-code\": print(\"XO $repo: no claude in terminal\")
elif s.get(\"state\") in (\"done\",\"idle\") and time.time()*1000-d.get(\"status_ms\",0)>1200000: print(\"XO $repo: CAG idle over 20 min\")
if load>32: print(\"XO $repo: load\",load)
' \"\$load\"
    hc read $term 2>/dev/null | tail -40 | grep -q 'Needs you (Commander)' && echo 'XO $repo: asks the commander'
    hc read $term 2>/dev/null | tail -40 | grep -q \"background shell command tasks didn't finish\" && echo 'XO $repo: lost background tasks'
    find ~/.cache/claude-shift -name '*.log' -mmin -15 -exec tail -1 {} \; 2>/dev/null | grep -q FAILED && echo 'XO $repo: roll FAILED (~/.cache/claude-shift)'
    git -C ~/Git/$repo fetch -q origin 2>/dev/null; echo \"MAIN \$(git -C ~/Git/$repo rev-parse origin/main)\"
  " 9>&- 2>&1 || true)
  fl=$(timeout 30 ssh -o ConnectTimeout=10 "$far" uptime 9>&- 2>&1 | sed -E 's/.*load averages?: *([0-9.]+).*/\1/' || true)
  alerts=""
  while read -r line; do
    [ -n "$line" ] && fresh "$line" && alerts="$alerts$line"$'\n'
  done < <(echo "$out" | grep -E '^XO|ssh:|timed out' || true)
  line="XO $far: load $fl"
  if awk "BEGIN{exit !($fl>32)}" 2>/dev/null && fresh "$line"; then alerts="$alerts$line"$'\n'; fi
  main=$(echo "$out" | sed -n 's/^MAIN //p')
  now=$(date +%s)
  if [ -n "$main" ] && [ "$main" != "$last_main" ]; then
    last_main=$main quiet_since=$now
    echo "$main $now" > "$dir/main"
  fi
  line="XO $repo: nothing landed on origin/main for 90 min"
  if [ $((now - quiet_since)) -gt 5400 ] && fresh "$line"; then alerts="$alerts$line"$'\n'; fi
  # Both buckets; gh issue and gh label spend GraphQL (docs/github-api.md).
  for b in core graphql; do
    q=$(gh api rate_limit -q ".resources.$b|\"\(.remaining) \(.reset)\"" 2>/dev/null || true)
    if [ -n "$q" ] && [ "${q% *}" -lt 500 ] && once "quota-$b-${q#* }"; then
      alerts="${alerts}XO github: $b quota at ${q% *}, resets $(date -r "${q#* }" +%H:%M)"$'\n'
    fi
  done
  # The check is silent without the switch file, or on a Prometheus failure.
  while read -r line; do
    [ -n "$line" ] && fresh "$line" && alerts="$alerts$line"$'\n'
  done < <(timeout 30 "$(dirname "$0")/xo-deepseek.py" 2>/dev/null || true)
  # Fast-forwards each host's toolbox; alerts only when it cannot (2026-11-21: two stale hosts).
  while read -r line; do
    [ -n "$line" ] && fresh "$line" && alerts="$alerts$line"$'\n'
  done < <(timeout 400 "$(dirname "$0")/xo-toolbox.py" "$dir/toolbox-stamp" 2>/dev/null || true)
  # Search ignores punctuation, so filter on the title's start.
  # A red main open 20 min means its fix is not moving (2026-11-20: two such held landings an hour each).
  # CAGs also title tool bugs fix(train).
  red=$(gh issue list -R "$slug" --state open --search 'in:title "fix(train): main is red"' --json number,createdAt,title \
    -q '.[]|select(.title|startswith("fix(train): main is red"))|"\(.number) \(.createdAt)"' 2>/dev/null || true)
  while IFS=" " read -r n at; do
    [ -n "$n" ] || continue
    age=$(((now - $(date -j -u -f '%Y-%m-%dT%H:%M:%SZ' "$at" +%s 2>/dev/null || echo "$now")) / 60))
    if [ "$age" -ge 20 ] && once "red-$repo-$n"; then alerts="${alerts}XO $repo: main red for $age min, #$n still open"$'\n'; fi
  done <<< "$red"
  # A CAG waiting on a background agent reads "working".
  while read -r line; do
    [ -n "$line" ] && fresh "$line" && alerts="$alerts$line"$'\n'
  done < <(timeout 90 "$(dirname "$0")/xo-work.py" --repo "$slug" --state "$dir/work.json" --cap "${XO_CAP:-6}" 2>/dev/null || true)
  if [ -r "$watch" ]; then
    while read -r n; do
      [ -n "$n" ] || continue
      if [ "$(gh issue view "$n" -R "$slug" --json state -q .state 2>/dev/null || true)" = CLOSED ] && once "closed-$n"; then
        alerts="${alerts}XO $repo: #$n closed"$'\n'
      fi
    done < "$watch"
  fi
  while read -r item; do
    [ -n "$item" ] && alerts="${alerts}XO due: $item"$'\n'
  done < <("$(dirname "$0")/xo-due" pop "$dir/due" || true)
  touch "$dir/heartbeat"
  if [ -n "$(echo "$alerts" | tr -d '[:space:]')" ]; then
    if [ "$once" = 1 ]; then
      printf '%s' "$alerts"
    else
      deliver "XO: $(printf '%s' "$alerts" | sed -E 's/^XO:? ?//' | paste -sd'|' - | sed 's/|/ | /g')" || true
    fi
  fi
  [ "$once" = 1 ] && exit 0
  sleep "$interval" 9>&-
done
