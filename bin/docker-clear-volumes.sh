#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Remove all Docker volumes

docker volume rm $(docker volume ls -q)
