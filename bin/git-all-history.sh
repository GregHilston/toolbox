#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Show the full history of a file, including renames and diffs

git log --follow -p -- "$@"
