#!/usr/bin/env bash
set -e

# update the apt repo
apt-get update \

# install things we care about
&& apt-get install -y \
git \
build-essential \
tmux \
vim \
htop \
zsh