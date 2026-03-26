#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Force-remove all Docker containers

docker rm -f $(docker ps -a -q)
