#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

cd docker

docker build -t toolbox .

cd ..