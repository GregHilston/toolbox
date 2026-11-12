#!/usr/bin/env bash
# Tab 1 of a `zj` session: Herdr, on a workspace named after the session.
# Focus only on create: `workspace focus` moves every open Herdr client.
set -euo pipefail
IFS=$'\n\t'

name=${1:-${ZELLIJ_SESSION_NAME:?run inside zellij or pass a name}}

if list=$(herdr workspace list 2>/dev/null) &&
  ! python3 -I -c 'import json,sys; sys.exit(sys.argv[1] not in [w["label"] for w in json.loads(sys.argv[2])["result"]["workspaces"]])' "$name" "$list"; then
  herdr workspace create --cwd "$PWD" --label "$name" --focus >/dev/null
fi

exec herdr
