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
    # python3 -m pip install --user ansible
    $SUDO apt-get update
    # Setting the DEBIAN_FRONTEND and TZ allows us to ignore the geographical
    # questionaire that comes from installing tzdata, which is a dependency
    DEBIAN_FRONTEND=noninteractive TZ=America/New_York $SUDO apt-get install ansible -y

    # Check if the PATH line is already present in ~/.bashrc
    PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'
    if ! grep -q "$PATH_LINE" ~/.bashrc; then
        echo "╔════════════════════════════════════════════════════════════╗"
        echo "║ ⚠                                                       ⚠  ║"
        echo "║                                                            ║"
        echo "║ I've added ansible to your PATH, this requires reloading   ║"
        echo "║ your bashrc. Be sure to do this, as ansible will not be    ║"
        echo "║ able to be ran. Run $ source ~/.bashrc to resolve this.    ║"
        echo "║                                                            ║"
        echo "║ ⚠                                                       ⚠  ║"
        echo "╚════════════════════════════════════════════════════════════╝"
        echo "$PATH_LINE" >> ~/.bashrc
    else
        echo "Ansible is already in PATH."
    fi

    echo "Ansible has been installed."
else
    echo "Ansible is already installed."
fi