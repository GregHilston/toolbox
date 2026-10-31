#!/bin/sh
# Gives each Agent-tool subagent a Herdr tab and sidebar row. A Claude Code
# hook: herdr-subagent.sh start|stop|end. Does nothing outside a Herdr pane.
#
# Hook input has no task or model, so they come from Claude's undocumented
# subagents/agent-<id>.meta.json. If it moves, tabs show the agent type.
[ "${HERDR_ENV:-}" = "1" ] || exit 0
in=$(cat)
session=$(printf '%s' "$in" | jq -r '.session_id // "unknown"')
id=$(printf '%s' "$in" | jq -r '.agent_id // empty')
type=$(printf '%s' "$in" | jq -r '.agent_type // "agent"')
parent=$(printf '%s' "$in" | jq -r '.transcript_path // empty')
root="${XDG_STATE_HOME:-$HOME/.local/state}/herdr-subagent"
dir="$root/$session"
mkdir -p "$dir"
exec 2>>"$root/hook.log"
PS4='+ $(date +%T) '
set -x
h="$HERDR_BIN_PATH"
base="${parent%.jsonl}/subagents/agent-$id"
case "$1" in
start)
  [ -n "$id" ] || exit 0
  # A subagent resumed from background work starts again.
  if pane=$(cat "$dir/$id" 2>/dev/null); then
    rm -f "$dir/$id.stop"
    "$h" pane report-agent "$pane" --source user:subagent --agent "$(cat "$dir/$id.name")" --state working --message resumed
    exit 0
  fi
  i=0
  until [ -s "$base.meta.json" ] || [ "$i" -ge 15 ]; do
    sleep 0.2
    i=$((i + 1))
  done
  desc=$(jq -r '.description // empty' "$base.meta.json")
  model=$(jq -r '.model // empty' "$base.meta.json")
  name="${model:-$type}"
  out=$("$h" tab create --workspace "$HERDR_WORKSPACE_ID" --label "$name: ${desc:-$type}" --no-focus) || exit 0
  pane=$(printf '%s' "$out" | jq -r '.result.root_pane.pane_id')
  printf '%s' "$pane" >"$dir/$id"
  printf '%s' "$name" >"$dir/$id.name"
  "$h" pane run "$pane" "$(dirname "$0")/herdr-subagent-view.sh '$base.jsonl'"
  "$h" pane report-agent "$pane" --source user:subagent --agent "$name" --state working --message "${desc:-$id}"
  ;;
stop)
  [ -n "$id" ] || exit 0
  pane=$(cat "$dir/$id" 2>/dev/null) || exit 0
  name=$(cat "$dir/$id.name" 2>/dev/null)
  "$h" pane report-agent "$pane" --source user:subagent --agent "${name:-$type}" --state idle --message done
  printf '%s' "$$" >"$dir/$id.stop"
  sleep "${HERDR_SUBAGENT_LINGER:-10}"
  [ "$(cat "$dir/$id.stop" 2>/dev/null)" = "$$" ] || exit 0
  "$h" pane close "$pane"
  rm -f "$dir/$id" "$dir/$id.name" "$dir/$id.stop"
  ;;
end)
  for f in "$dir"/*; do
    case "$f" in
    *.name | *.stop) continue ;;
    esac
    [ -f "$f" ] && "$h" pane close "$(cat "$f")"
    rm -f "$f" "$f.name" "$f.stop"
  done
  rmdir "$dir"
  ;;
esac
exit 0
