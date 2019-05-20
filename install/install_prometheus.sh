#!/usr/bin/env bash
set -e

docker run -d \
           -p 9090:9090 \
           -v /tmp/prometheus.yml:/etc/prometheus/prometheus.yml \
           --net pivpn \
           --name prometheus \
           rycus86/prometheus:2.7.1-armhf
