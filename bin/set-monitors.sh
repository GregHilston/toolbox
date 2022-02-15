#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

xrandr --output DP-0 --primary --mode 2560x1440 --pos 1080x0 --rotate normal --output DP-1 --off --output HDMI-0 --off --output DP-2 --mode 1920x1080 --pos 3640x0 --rotate right --output DP-3 --off --output DP-4 --mode 1920x1080 --pos 0x0 --rotate left --output DP-5 --off --output USB-C-0 --off
