#!/bin/bash
set -euo pipefail

# Copy stdin to the clipboard of the machine you are sitting at.
#
# Written for zellij's copy_command, which is a single string for every host
# this config is stowed to. Locally that means the native tool. Over SSH the
# native tool would copy on the far end -- dungeon has no clipboard at all --
# so write OSC 52 to $SSH_TTY instead: the sequence rides the connection back
# to the terminal you are actually looking at, which is what zellij does for
# itself when copy_command is unset.

payload=$(cat)

if [[ -n ${SSH_TTY:-} && -w ${SSH_TTY:-} ]]; then
  b64=$(printf '%s' "$payload" | base64 | tr -d '\n')
  printf '\033]52;c;%s\a' "$b64" > "$SSH_TTY"
  exit 0
fi

for c in pbcopy wl-copy "xclip -selection clipboard" xsel termux-clipboard-set; do
  if command -v "${c%% *}" >/dev/null 2>&1; then
    printf '%s' "$payload" | $c
    exit 0
  fi
done

echo "clipboard-copy: no clipboard tool, and no writable \$SSH_TTY" >&2
exit 1
