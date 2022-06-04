#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

echo "Ensuring this was not run with sudo..."

if [ "$(whoami)" == "root" ]; then
    echo "Do not run this command with root!"
    exit 1
fi

exit 0
