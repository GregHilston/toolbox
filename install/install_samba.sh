#!/usr/bin/env bash

# first make a mount point
mkdir -p /media/mothership

LINE='//retropie/mothership /media/mothership cifs guest,uid=1000,iocharset=utf8 0 0'
FILE='/etc/fstab'
grep -qF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"

mount -av
