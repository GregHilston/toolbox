#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Creates a timer for N seconds, leveraging text to speech for communication

seconds = $1

settimer() {
    say --voice karen "timer started"
    sleep $(echo "$seconds * 60" | bc)
    say --voice karen "timer done"
}
settimer $1
