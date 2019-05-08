#!/usr/bin/env bash
set -e

# from https://github.com/linuxserver/docker-organizr
# puid and pgid found by running
# $ id [username]
# example:
# $ id pi

docker rm organizr

docker run \
  --name=organizr \
  -e PUID=1000 \
  -e PGID=1000 \
  -e TZ=Denver \
  -p 9983:80 \
  -v ~/organizr-config:/config \
  --restart unless-stopped \
  linuxserver/organizr