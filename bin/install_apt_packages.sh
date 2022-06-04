#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

echo "Installing apt packages..."

# add repos
sudo add-apt-repository ppa:andreasbutti/xournalpp-master -y
sudo add-apt-repository ppa:nextcloud-devs/client -y
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc \
    | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null \
    && echo "deb https://ngrok-agent.s3.amazonaws.com buster main" \
    | sudo tee /etc/apt/sources.list.d/ngrok.list

# update the apt repo
sudo apt-get update -y

# most of our packages
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
ripgrep \
jq \
tldr \
ngrok

# docker
# Update the apt package index and install packages to allow apt to use a repository over HTTPS
sudo apt-get install \
    ca-certificates \
    curl \
    gnupg \
    lsb-release -y

# Add Docker’s official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Use the following command to set up the repository:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update the apt package index, and install the latest version of Docker Engine, containerd, and Docker Compose
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin -y
