#!/bin/bash

read -p 'remote ip address: ' remoteIp
read -p 'remote username: ' remoteUsername
read -sp 'remote password: ' remotePassword

echo $remoteIp
echo $remoteUsername

rsync -avxHAS --progress /mnt/user/backup/ $remoteUsername@$remoteIp:/media/hdd/backup/
