#!/usr/bin/env bash
set -e

TOOLBOX_DIR="$PWD"
source "$TOOLBOX_DIR/secret/env.sh"

sudo zerotier-one.zerotier-cli join $ZERO_TIER_NEXTWORK_ID
sudo zerotier-one.zerotier-cli info
