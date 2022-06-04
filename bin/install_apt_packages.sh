#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

echo "Installing apt packages..."

# add repos
sudo add-apt-repository ppa:andreasbutti/xournalpp-master -y
sudo add-apt-repository ppa:nextcloud-devs/client -y

# update the apt repo
sudo apt-get update -y

# install things we care about
sudo apt-get install -y \
git \
build-essential \
tmux \
curl \
mosh \
vim \
htop \
zsh \
ansible \
python3-dev \
python3-pip \
python3-setuptools \
xournalpp \
i3 \
i3lock \
i3status \
kde-standard \
redshift \
redshift-gtk \
tree \
lynx \
suckless-tools \
blueman \
arandr \
nextcloud-client \
ranger \
neovim \
thefuck \
timeshift \
fzf \
ripgrep

