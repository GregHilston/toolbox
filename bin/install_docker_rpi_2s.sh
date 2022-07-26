#!/usr/bin/env bash
set -e

# For older pis

sudo apt-get update

# install an old version that works on our old pi
sudo apt-get install docker-ce=18.06.1~ce~3-0~raspbian

# add our user to the docker group so we don't need to use sudo
sudo usermod -aG docker $USER