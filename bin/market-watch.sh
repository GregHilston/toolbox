#!/bin/bash
# The Craigslist search terms dungeon's market bot watches: list, add, remove.
#
# The list lives in the hermes container's digest state, so this runs
# `digest watch` there: directly on dungeon, over ssh anywhere else.
# The market bot's Telegram tool calls the same command.
set -euo pipefail
IFS=$'\n\t'

usage() { echo "usage: market-watch.sh list | add <term> | remove <term>" >&2; exit 2; }
action=${1:-}
case "$action" in
  list) args=(list) ;;
  add|remove) shift; [ $# -gt 0 ] || usage; args=("$action" -- "$*") ;;
  *) usage ;;
esac

cmd=(docker exec hermes bash -c 'source /opt/data/scripts/digest-env.sh && digest watch "$@"' - "${args[@]}")
if docker inspect hermes >/dev/null 2>&1; then
  exec "${cmd[@]}"
fi
# A non-interactive ssh shell has no OrbStack on PATH.
exec ssh dungeon "PATH=\$HOME/.orbstack/bin:/usr/local/bin:\$PATH $(printf '%q ' "${cmd[@]}")"
