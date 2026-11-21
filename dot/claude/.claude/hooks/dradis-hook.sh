#!/usr/bin/env bash
# Post a Claude hook event to the dradis core, or arm its idle wake.
# Usage: dradis-hook.sh <Event|wake>. A dead core passes.
#
# Not an HTTP hook: Claude Code refuses tailnet addresses (100.64/10) and
# allows only loopback, so moria and foundation cannot reach the core with one.
event=${1:?event}
url=${DRADIS_URL:-https://dungeon.tail1b9d9.ts.net:10000/factory}

# Only these repos feed the factory; a worktree counts as its main repo.
repos=${DRADIS_REPOS:-gridkeep loser-picks toolbox notes dradis}
input=
[[ -t 0 ]] || input=$(cat)
cwd=$PWD
[[ $input =~ \"cwd\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]] && cwd=${BASH_REMATCH[1]}
common=$(git -C "$cwd" rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || exit 0
repo=${common%/.git}
repo=${repo##*/}
[[ " $repos " == *" $repo "* ]] || exit 0

# dungeon's `hc` names a remote terminal <machine>/<id>; its own are bare.
case ${DRADIS_HOST:-${HOSTNAME%%.*}} in
  moria) prefix=moriats/ ;;
  foundation) prefix=foundationts/ ;;
  *) prefix= ;;
esac
terminal=
[[ -n "${HC_TERMINAL_ID:-}" ]] && terminal=$prefix$HC_TERMINAL_ID

if [[ $event == wake ]]; then
  script="${DRADIS_HOME:-$HOME/Git/dradis}/hooks/wake.sh"
  [[ -x $script ]] || exit 0
  HC_TERMINAL_ID=$terminal DRADIS_URL=$url exec "$script"
fi

# Only these two answer with something Claude acts on.
out=/dev/null
case $event in PostToolBatch | Stop) out=/dev/stdout ;; esac

printf %s "$input" | curl -s --fail --max-time 1 -X POST -H 'Content-Type: application/json' \
  ${terminal:+-H "X-Hc-Terminal: $terminal"} --data-binary @- \
  -o "$out" "$url/hooks/$event" || true
exit 0
