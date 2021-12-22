#!/bin/bash
set -euo pipefail
IFS=$'\n\t'


cat $TOOLBOX_HOME/dot/i3-gaps/config-base \
    $TOOLBOX_HOME/dot/i3-gaps/config-$(hostname) > $HOME/.config/i3/config
