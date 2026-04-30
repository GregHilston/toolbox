#!/usr/bin/env bash
# aerospace-save-state.sh — Snapshot AeroSpace window state before a restart.
#
# AeroSpace has no built-in state persistence (see upstream issue #57). When the
# process is killed and restarted — e.g. during `darwin-rebuild switch` — every
# window loses its workspace assignment and gets dumped onto the focused workspace.
# Minimized windows are even worse: AeroSpace un-minimizes them on restart because
# it discovers them as "new" windows.
#
# This script captures two things:
#   1. Window-to-workspace mappings via `aerospace list-windows` (only sees
#      non-minimized windows that AeroSpace is currently managing).
#   2. Minimized window state via the macOS Accessibility API (AXMinimized
#      attribute through System Events), which catches windows that AeroSpace
#      doesn't track at all.
#
# Output files:
#   ~/.aerospace-windows.json    — array of {window-id, workspace, app-name, window-title}
#   ~/.aerospace-minimized.json  — array of {app, title} for minimized windows
#   ~/.aerospace-windows-focused.txt — the focused workspace number
#
# Pair with aerospace-restore-state.sh to restore state after the restart.

set -euo pipefail
IFS=$'\n\t'

STATE_FILE="$HOME/.aerospace-windows.json"
MINIMIZED_FILE="$HOME/.aerospace-minimized.json"

if ! command -v aerospace &>/dev/null; then
  echo "[aerospace] not found, skipping state save"
  exit 0
fi

# Save workspace assignments (aerospace only sees non-minimized windows)
if ! aerospace list-windows --all --json --format '%{window-id}%{workspace}%{app-name}%{window-title}' > "$STATE_FILE" 2>/dev/null; then
  echo "[aerospace] failed to list windows, skipping state save"
  rm -f "$STATE_FILE"
  exit 0
fi

# Save minimized window state via macOS Accessibility API.
# AeroSpace doesn't expose a "minimized" format variable, and `list-windows --all`
# silently omits minimized windows entirely. We have to go through System Events
# and read the AXMinimized attribute on every window of every foreground process.
# This works universally across Cocoa, Electron, and other app frameworks — unlike
# the per-app AppleScript scripting bridge (e.g. `miniaturized` only works in apps
# like Firefox that implement the NSWindow scripting dictionary).
osascript -e '
set output to "["
set needComma to false
tell application "System Events"
  set allProcs to every process whose background only is false
  repeat with proc in allProcs
    set procName to name of proc
    try
      repeat with w in (every window of proc)
        set wMin to value of attribute "AXMinimized" of w
        if wMin then
          set wTitle to name of w
          if needComma then set output to output & ","
          set output to output & "{\"app\":\"" & procName & "\",\"title\":\"" & wTitle & "\"}"
          set needComma to true
        end if
      end repeat
    end try
  end repeat
end tell
set output to output & "]"
return output
' > "$MINIMIZED_FILE" 2>/dev/null || echo "[]" > "$MINIMIZED_FILE"

# Save focused workspace so we can return the user to where they were
FOCUSED=$(aerospace list-workspaces --focused 2>/dev/null || echo "")
if [[ -n "$FOCUSED" ]]; then
  echo "$FOCUSED" > "${STATE_FILE%.json}-focused.txt"
fi

WIN_COUNT=$(jq 'length' "$STATE_FILE" 2>/dev/null || echo 0)
MIN_COUNT=$(jq 'length' "$MINIMIZED_FILE" 2>/dev/null || echo 0)
echo "[aerospace] saved $WIN_COUNT window assignments + $MIN_COUNT minimized windows"
