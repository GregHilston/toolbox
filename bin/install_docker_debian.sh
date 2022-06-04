#!/usr/bin/env bash
set -e

# From https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-on-ubuntu-18-04

# First, update your existing list of packages:
apt update

# Next, install a few prerequisite packages which let apt use packages over HTTPS:
apt install apt-transport-https ca-certificates curl software-properties-common -y

# Then add the GPG key for the official Docker repository to your system:
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -

# Add the Docker repository to APT sources:
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable"

# Next, update the package database with the Docker packages from the newly added repo:
apt update

# Make sure you are about to install from the Docker repo instead of the default Ubuntu repo:
apt-cache policy docker-ce

# You'll see output like this, although the version number for Docker may be different:
# docker-ce:
# Installed: (none)
# Candidate: 18.03.1~ce~3-0~ubuntu
# Version table:
    # 18.03.1~ce~3-0~ubuntu 500
    # 500 https://download.docker.com/linux/ubuntu bionic/stable amd64 Packages

# Notice that docker-ce is not installed, but the candidate for installation is from the Docker repository for Ubuntu 18.04 (bionic). 

# Finally, install Docker:
apt install docker-ce systemd -y

@echo "Docker should now be installed, the daemon started, and the process enabled to start on boot. Check that it's running by running '\$sudo systemctl status docker'"
