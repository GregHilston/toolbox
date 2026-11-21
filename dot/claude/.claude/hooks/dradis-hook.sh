#!/usr/bin/env bash
# Post a Claude hook event to the dradis core, or arm its idle wake.
# Usage: dradis-hook.sh <Event|wake>. A dead core passes.
#
# Not an HTTP hook: Claude Code refuses tailnet addresses (100.64/10) and
# allows only loopback, so moria and foundation cannot reach the core with one.
event=${1:?event}
url=${DRADIS_URL:-https://dungeon.tail1b9d9.ts.net:10000/factory}

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

curl -s --fail --max-time 1 -X POST -H 'Content-Type: application/json' \
  ${terminal:+-H "X-Hc-Terminal: $terminal"} --data-binary @- \
  -o "$out" "$url/hooks/$event" || true
exit 0
