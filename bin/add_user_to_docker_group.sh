#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

echo "Adding $USER to Docker group"

# This is to ensure we have a proper reference to our non-root user with the $USER command
./bin/ensure_no_sudo.sh

# -f allows this command to exit with a success code if the group already exists
sudo groupadd -f docker
sudo usermod -aG docker $USER

# reloading so we don't have to log out then back in
newgrp docker
