#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Start a timer for N minutes with text-to-speech announcements

minutes="${1:?Usage: timer.sh <minutes>}"

say --voice karen "timer started"
sleep $(echo "$minutes * 60" | bc)
say --voice karen "timer done"
