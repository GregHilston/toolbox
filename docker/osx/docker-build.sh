#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

cd docker/osx

docker build -t toolbox-osx --build-arg SHORTNAME=ventura .

cd ../..

