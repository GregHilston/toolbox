#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Undo the last commit, keeping changes staged

git reset --soft HEAD^
