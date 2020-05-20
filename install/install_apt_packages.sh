#!/usr/bin/env bash
set -e

# add repos
sudo add-apt-repository ppa:andreasbutti/xournalpp-master -y

# update the apt repo
sudo apt-get update

# install things we care about
sudo apt-get install -y \
git \
build-essential \
tmux \
mosh \
vim \
htop \
zsh \
ansible \
python3-dev \
python3-pip \
python3-setuptools \
xournalpp \
snapd
# samba samba-common-bin
