#!/usr/bin/env bash
set -e

# update the apt repo
apt-get update

# install things we care about
apt-get install -y \
git \
build-essential \
tmux \
mosh \
vim \
htop \
zsh
# samba samba-common-bin