#!/usr/bin/env bash
# Usage: chain.sh <model>=<arm> ...   Runs crud_eval.py once per pair, in order.
set -u
cd "$(dirname "$0")"
export OMLX_API_KEY=${OMLX_API_KEY:-$(python3 -c "import json,os;print(json.load(open(os.path.expanduser('~/.omlx/settings.json')))['auth']['api_key'])")}
for pair in "$@"; do
  echo "=== ${pair#*=}"
  python3 crud_eval.py "${pair%%=*}" "${pair#*=}" ${EXTRA_ARGS:-} 2>&1
done
