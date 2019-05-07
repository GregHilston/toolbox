#!/usr/bin/env bash
set -e

docker run \
-d \
--privileged \
--name plex \
--net=host \
-v /media/mothership:/media/mothership \
-e TZ="America/Denver" \
-e PLEX_CLAIM="" \
-e ADVERTISE_IP="http://10.0.0.2" \
-h 10.0.0.2 \
lsioarmhf/plex
