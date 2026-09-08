#!/bin/bash
set -euo pipefail

# Copy stdin to the system clipboard, whichever clipboard this host has.
#
# Exists for zellij's copy_command, which takes one command for every host the
# config is stowed to. Note it copies to the clipboard of the machine zellij
# runs on: over SSH that is the remote, where OSC 52 would have reached the
# terminal. Drop copy_command to get that back.

for c in pbcopy wl-copy "xclip -selection clipboard" xsel termux-clipboard-set; do
  if command -v "${c%% *}" >/dev/null 2>&1; then
    exec $c
  fi
done

echo "clipboard-copy: no clipboard tool found" >&2
exit 1
