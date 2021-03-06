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
           -v ~/.organizr-config:/config \
           -e PGID=1000 \
           -e PUID=1000 \
           -p 80:80 \
           -d \
           --restart unless-stopped \
           organizrtools/organizr-v2:armhf
