#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Lists the IP addresess in use, on the network

arp -a | awk '{print $2 " " $1}' | sort -V

# alternative approach:
# sudo nmap -sn 192.168.1.0/24
