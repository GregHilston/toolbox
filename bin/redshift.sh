#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Toggles whether a night time blue light filter is running or not

state_file="/tmp/redshift_toggle_state"

# Check if the state file exists and read the toggle state
if [ -e "$state_file" ]; then
    toggle_redshift=$(cat "$state_file")
else
    toggle_redshift=true
fi

if [ "$toggle_redshift" = true ]; then
    redshift -l 44.8:-73 -t 5800:3600 -g 0.8 -m randr -v
else
    # undo redshift
    redshift -x
fi

# Save the toggle state to the file
echo "$toggle_redshift" > "$state_file"
