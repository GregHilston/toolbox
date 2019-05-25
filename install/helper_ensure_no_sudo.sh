#!/usr/bin/env bash
set -e

if [ "$(whoami)" == "root" ]; then
    echo "Do not run this command with root!"
    exit 1
fi

exit 0
