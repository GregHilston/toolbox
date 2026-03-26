#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Recursively search for a file by name in the current directory

find . -name "${1}"
