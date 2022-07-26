#!/usr/bin/env bash
set -e

# fetcy the deb package
wget --directory-prefix=/var/tmp/ https://download.teamviewer.com/download/linux/teamviewer_amd64.deb

# install things we care about
sudo apt-get install /var/tmp/teamviewer_amd64.deb -y
