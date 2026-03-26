#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Force-remove all Docker images

docker rmi -f $(docker images -a -q)
