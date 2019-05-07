#!/usr/bin/env bash
set -e

docker create \
  --name=organizr \
  -e PUID=1000 \
  -e PGID=1000 \
  -e TZ=<your timezone, eg Europe/London> \
  -p 9983:80 \
  -v <path to data>:/config \
  --restart unless-stopped \
  linuxserver/organizr