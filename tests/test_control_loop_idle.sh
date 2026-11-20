#!/usr/bin/env bash
# The XO alerts on a CAG idle over 20 min, and only then.
set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
py=$(awk '/hc get \$term --json/{on=1;next} on&&/^'"'"'/{exit} on' "$here/bin/control-loop.sh" | sed 's/\\"/"/g; s/\$repo/lp/g')
now=$(($(date +%s) * 1000))
check() { # check <state> <minutes ago> <expect alert 0|1>
  local json got
  json="{\"state\":\"live\",\"status\":{\"app\":\"claude-code\",\"state\":\"$1\"},\"status_ms\":$((now - $2 * 60000))}"
  got=$(echo "$json" | python3 -c "$py" 1 | grep -c "idle over 20 min" || true)
  [ "$got" = "$3" ] || { echo "FAIL: $1 for $2 min gave $got alerts, want $3"; exit 1; }
}
check done 21 1
check idle 30 1
check done 5 0
check working 60 0
echo ok
