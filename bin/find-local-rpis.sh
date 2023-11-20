#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# This script leverages the fact that Raspberry Pis have a specific mac address
# format. It will print all ip addresess of Raspberry Pis found on the network.

nmap -sP 192.168.1.0/24 | awk '/^Nmap/{ip=$NF}/B8:27:EB/{print ip}'