#!/usr/bin/env bash
set -e

# this is because raspberry pis have a specific mac address format
nmap -sP 192.168.1.0/24 | awk '/^Nmap/{ip=$NF}/B8:27:EB/{print ip}'