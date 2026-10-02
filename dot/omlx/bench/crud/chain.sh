#!/usr/bin/env bash
# Usage: [EXTRA_ARGS="--host dungeon"] chain.sh <model>=<arm> ...
# Runs crud_eval.py once per pair, in order. No -e: one failed arm must not stop the rest.
set -u
cd "$(dirname "$0")" || exit 1
export OMLX_API_KEY=${OMLX_API_KEY:-$(python3 -c "import json,os;print(json.load(open(os.path.expanduser('~/.omlx/settings.json')))['auth']['api_key'])")}
read -ra extra <<< "${EXTRA_ARGS:-}"
for pair in "$@"; do
  echo "=== ${pair#*=}"
  python3 crud_eval.py "${pair%%=*}" "${pair#*=}" "${extra[@]}" 2>&1
done
