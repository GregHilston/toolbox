#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Installs any and all dependencies required to get the toolbox install.sh script to work

# Check if the script is running as root (in a Docker container). If so, we do
# not need to use sudo. If not, then we do need to use sudo.
if [ "$(id -u)" = "0" ]; then
    SUDO=""
else
    SUDO="sudo"
fi

# Check if Ansible is installed
if ! command -v ansible &> /dev/null; then
    echo "Ansible is not installed. Installing Ansible..."

    $SUDO apt-get update
    $SUDO apt-get install ansible -y

    echo "Ansible has been installed."
else
    echo "Ansible is already installed."
fi

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║ You should be good to run install.sh now                   ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
