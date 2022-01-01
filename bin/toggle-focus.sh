#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

TOGGLE=$HOME/.focus-mode-toggle-file
FOCUS="xrandr --output DP-4 --brightness 0.0 && xrandr --output DP-2 --brightness 0.0"
UNFOCUS="xrandr --output DP-4 --brightness 1.0 && xrandr --output DP-2 --brightness 1.0"

if [ ! -e $TOGGLE ]; then
    echo "Enabling focus mode"
    touch $TOGGLE
    eval "$FOCUS"
else
    echo "Disabling focus mode"
    rm $TOGGLE
    eval "$UNFOCUS"
fi
