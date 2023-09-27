#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

echo "Installing flatpaks..."

flatpak install flathub com.slack.Slack -y
flatpak install flathub com.spotify.Client -y
flatpak install flathub com.bitwarden.desktop -y
flatpak install flathub md.obsidian.Obsidian -y
flatpak install flathub com.visualstudio.code -y
