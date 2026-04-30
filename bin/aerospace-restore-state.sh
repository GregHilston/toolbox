#!/usr/bin/env bash
# aerospace-restore-state.sh — Restore AeroSpace window state after a restart.
#
# Reads the state files written by aerospace-save-state.sh and performs three
# steps in order:
#
#   Step 1: Re-minimize windows.
#     Uses the macOS Accessibility API (System Events + AXMinimized) to push
#     previously-minimized windows back to the dock. This must happen BEFORE
#     workspace reassignment — otherwise AeroSpace sees these windows as
#     visible, tiles them, and they displace the windows you actually want.
#
#   Step 2: Restore workspace assignments.
#     For each window AeroSpace currently knows about, find where it was before
#     the restart and move it back. Uses a three-tier matching strategy:
#       a) Exact window ID match (stable when only AeroSpace restarts, not apps)
#       b) App-name + window-title match (catches windows that got new IDs)
#       c) Sole-window-per-app match (if an app has exactly one window in both
#          saved and current state, assume they're the same)
#
#   Step 3: Restore focused workspace.
#     Switch back to whichever workspace the user was looking at before the
#     restart.
#
# Input files (all cleaned up after restore):
#   ~/.aerospace-windows.json
#   ~/.aerospace-minimized.json
#   ~/.aerospace-windows-focused.txt
#
# Both scripts are designed to be safe no-ops when AeroSpace isn't installed
# or state files don't exist, so they won't break `just dr` on machines that
# don't use AeroSpace.

set -euo pipefail
IFS=$'\n\t'

STATE_FILE="$HOME/.aerospace-windows.json"
MINIMIZED_FILE="$HOME/.aerospace-minimized.json"
FOCUSED_FILE="${STATE_FILE%.json}-focused.txt"

if [[ ! -f "$STATE_FILE" ]]; then
  echo "[aerospace] no saved state found, skipping restore"
  exit 0
fi

if ! command -v aerospace &>/dev/null; then
  echo "[aerospace] not found, skipping restore"
  exit 0
fi

# Wait for AeroSpace to be ready (it restarts during darwin-rebuild)
MAX_WAIT=15
for i in $(seq 1 "$MAX_WAIT"); do
  if aerospace list-windows --all &>/dev/null; then
    break
  fi
  if [[ $i -eq $MAX_WAIT ]]; then
    echo "[aerospace] timed out waiting for AeroSpace to start, skipping restore"
    exit 0
  fi
  sleep 1
done

# Give AeroSpace a moment to fully index all windows after startup
sleep 2

# --- Step 1: Re-minimize windows that were minimized before ---
MIN_RESTORED=0
if [[ -f "$MINIMIZED_FILE" ]] && [[ "$(jq 'length' "$MINIMIZED_FILE" 2>/dev/null)" != "0" ]]; then
  # Build an AppleScript that re-minimizes each saved window by app+title
  APPLESCRIPT='tell application "System Events"'$'\n'
  while IFS=$'\t' read -r app title; do
    # Escape backslashes and double quotes for AppleScript string
    escaped_title=$(echo "$title" | sed 's/\\/\\\\/g; s/"/\\"/g')
    APPLESCRIPT+="  try"$'\n'
    APPLESCRIPT+="    tell process \"$app\""$'\n'
    APPLESCRIPT+="      repeat with w in (every window)"$'\n'
    APPLESCRIPT+="        if name of w is \"$escaped_title\" then"$'\n'
    APPLESCRIPT+="          set value of attribute \"AXMinimized\" of w to true"$'\n'
    APPLESCRIPT+="        end if"$'\n'
    APPLESCRIPT+="      end repeat"$'\n'
    APPLESCRIPT+="    end tell"$'\n'
    APPLESCRIPT+="  end try"$'\n'
    MIN_RESTORED=$((MIN_RESTORED + 1))
  done < <(jq -r '.[] | [.app, .title] | @tsv' "$MINIMIZED_FILE")
  APPLESCRIPT+="end tell"

  osascript -e "$APPLESCRIPT" 2>/dev/null || true
fi

# --- Step 2: Restore workspace assignments for visible windows ---
CURRENT=$(aerospace list-windows --all --json --format '%{window-id}%{workspace}%{app-name}%{window-title}' 2>/dev/null)

RESTORED=0
FAILED=0

while IFS=$'\t' read -r cur_id cur_ws cur_app cur_title; do
  # First try: exact window ID match in saved state
  target_ws=$(jq -r --argjson id "$cur_id" '.[] | select(."window-id" == $id) | .workspace' "$STATE_FILE" 2>/dev/null)

  # Second try: match by app-name + window-title
  if [[ -z "$target_ws" ]]; then
    target_ws=$(jq -r --arg app "$cur_app" --arg title "$cur_title" \
      '.[] | select(."app-name" == $app and ."window-title" == $title) | .workspace' \
      "$STATE_FILE" 2>/dev/null)
  fi

  # Third try: if app has exactly one window in both saved and current, match by app-name
  if [[ -z "$target_ws" ]]; then
    saved_count=$(jq --arg app "$cur_app" '[.[] | select(."app-name" == $app)] | length' "$STATE_FILE" 2>/dev/null)
    current_count=$(echo "$CURRENT" | jq --arg app "$cur_app" '[.[] | select(."app-name" == $app)] | length' 2>/dev/null)
    if [[ "$saved_count" == "1" && "$current_count" == "1" ]]; then
      target_ws=$(jq -r --arg app "$cur_app" '.[] | select(."app-name" == $app) | .workspace' "$STATE_FILE" 2>/dev/null)
    fi
  fi

  # Skip if no match or already on the right workspace
  if [[ -z "$target_ws" || "$target_ws" == "$cur_ws" ]]; then
    continue
  fi

  if aerospace move-node-to-workspace --window-id "$cur_id" "$target_ws" </dev/null 2>/dev/null; then
    RESTORED=$((RESTORED + 1))
  else
    FAILED=$((FAILED + 1))
  fi
done < <(echo "$CURRENT" | jq -r '.[] | [."window-id", .workspace, ."app-name", ."window-title"] | @tsv')

# --- Step 3: Restore focused workspace ---
if [[ -f "$FOCUSED_FILE" ]]; then
  FOCUSED=$(cat "$FOCUSED_FILE")
  aerospace workspace "$FOCUSED" 2>/dev/null || true
  rm -f "$FOCUSED_FILE"
fi

rm -f "$STATE_FILE" "$MINIMIZED_FILE"
echo "[aerospace] restored $RESTORED windows ($FAILED failed), re-minimized $MIN_RESTORED"
