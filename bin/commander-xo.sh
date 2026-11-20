#!/bin/bash
# commander-xo.sh [interval-seconds]: the commander's XO (docs/commander.md). Checks one
# orchestrator every 10 min and exits with one "XO ..." line per problem, which wakes the
# commander; it also exits after 115 min so the commander re-arms it inside Claude's 2 h cap.
# Env: XO_HOST (moriats), XO_TERM (t17), XO_REPO (loser-picks), XO_FAR (foundationts),
# XO_CLOSES ("355 378": exit when any of these tickets closes).
host=${XO_HOST:-moriats} term=${XO_TERM:-t17} repo=${XO_REPO:-loser-picks} far=${XO_FAR:-foundationts}
slug=GregHilston/$repo
interval=${1:-600}
deadline=$(( $(date +%s) + 6900 ))
seen=~/.cache/commander-xo
mkdir -p "$seen"
last_main=""
quiet_since=$(date +%s)
once() { # once <key>: true the first time a key is seen
  [ -e "$seen/$1" ] && return 1
  : > "$seen/$1"
}
while :; do
  out=$(timeout 60 ssh -o ConnectTimeout=10 "$host" "
    load=\$(uptime | sed -E 's/.*load averages?: *([0-9.]+).*/\1/')
    hc get $term --json 2>/dev/null | python3 -c '
import json,sys
d=json.load(sys.stdin); s=d.get(\"status\") or {}
load=float(sys.argv[1])
if d.get(\"state\")!=\"live\": print(\"XO $repo: terminal\",d.get(\"state\"))
elif s.get(\"state\")==\"blocked\": print(\"XO $repo: blocked:\",(s.get(\"msg\") or \"\")[:200])
elif s.get(\"app\")!=\"claude-code\": print(\"XO $repo: no claude in terminal\")
if load>32: print(\"XO $repo: load\",load)
' \"\$load\"
    hc read $term 2>/dev/null | tail -40 | grep -q 'Needs you (Commander)' && echo 'XO $repo: asks the commander'
    hc read $term 2>/dev/null | tail -40 | grep -q \"background shell command tasks didn't finish\" && echo 'XO $repo: lost background tasks'
    find ~/.cache/claude-shift -name '*.log' -mmin -15 -exec tail -1 {} \; 2>/dev/null | grep -q FAILED && echo 'XO $repo: roll FAILED (~/.cache/claude-shift)'
    git -C ~/Git/$repo fetch -q origin 2>/dev/null; echo \"MAIN \$(git -C ~/Git/$repo rev-parse origin/main)\"
  " 2>&1)
  fl=$(timeout 30 ssh -o ConnectTimeout=10 "$far" uptime 2>&1 | sed -E 's/.*load averages?: *([0-9.]+).*/\1/')
  alerts=$(echo "$out" | grep -E '^XO|ssh:|timed out')
  awk "BEGIN{exit !($fl>32)}" 2>/dev/null && alerts="$alerts
XO $far: load $fl"
  main=$(echo "$out" | sed -n 's/^MAIN //p')
  now=$(date +%s)
  if [ -n "$main" ] && [ "$main" != "$last_main" ]; then last_main=$main; quiet_since=$now; fi
  [ $(( now - quiet_since )) -gt 5400 ] && alerts="$alerts
XO $repo: nothing landed on origin/main for 90 min"
  # Both buckets; gh issue and gh label spend GraphQL (docs/github-api.md).
  for b in core graphql; do
    q=$(gh api rate_limit -q ".resources.$b|\"\(.remaining) \(.reset)\"" 2>/dev/null)
    [ -n "$q" ] && [ "${q% *}" -lt 500 ] && once "quota-$b-${q#* }" && alerts="$alerts
XO github: $b quota at ${q% *}, resets $(date -r "${q#* }" +%H:%M)"
  done
  # Search ignores punctuation, so filter on the title's start.
  # A red main open 20 min means its fix is not moving (2026-11-20: two such held landings an hour each).
  red=$(gh issue list -R "$slug" --state open --search 'in:title "fix(train):"' --json number,createdAt,title \
    -q '.[]|select(.title|startswith("fix(train):"))|"\(.number) \(.createdAt)"' 2>/dev/null)
  while read -r n at; do
    [ -n "$n" ] || continue
    age=$(( (now - $(date -j -u -f '%Y-%m-%dT%H:%M:%SZ' "$at" +%s 2>/dev/null || echo "$now")) / 60 ))
    [ "$age" -ge 20 ] && once "red-$repo-$n" && alerts="$alerts
XO $repo: main red for ${age} min, #$n still open"
  done <<< "$red"
  for n in ${XO_CLOSES-}; do
    [ "$(gh issue view "$n" -R "$slug" --json state -q .state 2>/dev/null)" = CLOSED ] && alerts="$alerts
XO $repo: #$n closed"
  done
  if [ -n "$(echo "$alerts" | tr -d '[:space:]')" ]; then date '+%H:%M'; echo "$alerts"; exit 0; fi
  [ "$now" -gt "$deadline" ] && { date '+%H:%M'; echo "XO: 115 min up, re-arm"; exit 0; }
  sleep "$interval"
done
