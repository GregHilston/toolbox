#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Remove all user-created Docker networks (preserves bridge, none, host)

docker network rm $(docker network ls | tail -n+2 | awk '{if($2 !~ /bridge|none|host/){ print $1 }}')
