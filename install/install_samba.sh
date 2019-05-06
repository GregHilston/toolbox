#!/usr/bin/env bash
set -e

# first make a mount point
mkdir -p /media/mothership

# ensures we're only appending our LINE if it doesn't already in FILE
LINE='//retropie/mothership /media/mothership cifs guest,uid=1000,iocharset=utf8 0 0'
FILE='/etc/fstab'
grep -qF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"

mount -av