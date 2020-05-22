#!/usr/bin/env bash
set -e

# From https://linuxize.com/post/how-to-install-python-3-7-on-ubuntu-18-04/

# Start by updating the packages list and installing the prerequisites:
apt update
apt install software-properties-common -y

# Next, add the deadsnakes PPA to your sources list:
add-apt-repository ppa:deadsnakes/ppa -y

# Once the repository is enabled, install Python 3.7 and venv:
apt install python3.7 python3.7-venv -y

# At this point, Python 3.7 is installed on your Ubuntu system and ready to be used.
echo "Python3.7 should be installed, use by running '\$ python3.7'"
python3.7 --version
