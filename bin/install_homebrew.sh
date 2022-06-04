#!/usr/bin/env bash
set -e

SCRIPT_HOME=$(cd "$(dirname $0)" && pwd)
TOOLBOX_HOME=$(echo $SCRIPT_HOME | rev | cut -d/ -f2- | rev)
HOME=$($SCRIPT_HOME/helper_get_home_directory.sh)

/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
