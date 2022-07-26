#!/usr/bin/env bash
set -e

# For newer pis

# fetch the commands to run
curl -fsSL get.docker.com -o get-docker.sh && sh get-docker.sh

# add our user to the docker group so we don't need to use sudo
sudo usermod -aG docker $USER