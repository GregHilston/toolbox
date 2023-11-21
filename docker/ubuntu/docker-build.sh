#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

cd docker/ubuntu

docker build -t toolbox-ubuntu .

cd ../..
