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

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Installing Python 3..."
    $SUDO apt update
    $SUDO apt install -y python3
    echo "Python 3 has been installed."
else
    echo "Python 3 is already installed."
fi

# Check if pip for Python 3 is installed
if ! command -v pip3 &> /dev/null; then
    echo "pip for Python 3 is not installed. Installing pip for Python 3..."
    $SUDO apt update
    $SUDO apt install -y python3-pip
    echo "pip for Python 3 has been installed."
else
    echo "pip for Python 3 is already installed."
fi

# Check if Ansible is installed
if ! command -v ansible &> /dev/null; then
    echo "Ansible is not installed. Installing Ansible using pip..."
    python3 -m pip install --user ansible

    # Check if the PATH line is already present in ~/.bashrc
    PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'
    if ! grep -q "$PATH_LINE" ~/.bashrc; then
        echo "Adding ansible to PATH, requires reloading of bashrc"
        echo "$PATH_LINE" >> ~/.bashrc
    else
        echo "Ansible is already in PATH."
    fi

    echo "Ansible has been installed."
else
    echo "Ansible is already installed."
fi