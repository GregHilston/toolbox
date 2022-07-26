#!/usr/bin/env bash
set -e

# From https://linuxize.com/post/how-to-install-python-3-7-on-ubuntu-18-04/

# Start by updating the packages list and installing the prerequisites:
sudo apt update
sudo apt install software-properties-common -y

# Next, add the deadsnakes PPA to your sources list:
sudo add-apt-repository ppa:deadsnakes/ppa -y

# Once the repository is enabled, install Python 3.7 and venv:
sudo apt install python3.7 python3.7-venv -y

# At this point, Python 3.7 is installed on your Ubuntu system and ready to be used.
echo "Python3.7 should be installed, use by running '\$ python3.7'"
python3.7 --version

echo "We do not update the python alias, as this violates PEP 394, we update the python3 alias in ~/.zshrc. THIS MUST BE SOURCED AFTER RUNNING THIS SCRIPT."
