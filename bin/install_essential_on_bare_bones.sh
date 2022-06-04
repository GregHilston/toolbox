#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

apt-get update  && apt-get install git build-essential -y
