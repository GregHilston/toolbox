#!/usr/bin/env bash
set -e

docker run \
           -d \
           -i \
           -p 3000:3000 \
           --net pivpn \
           --name grafana \
           fg2it/grafana-armhf:v4.1.2
