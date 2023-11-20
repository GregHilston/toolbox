#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Performs a speed test

curl -s https://raw.githubusercontent.com/sivel/speedtest-cli/master/speedtest.py | python -
