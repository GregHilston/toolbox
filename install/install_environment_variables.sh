#!/usr/bin/env bash
set -e

# Work in progress

TOOLBOX_DIR="$PWD"
TOOLBOX_BIN_DIR="$TOOLBOX_DIR/../bin"
TOOLBOX_DOT_DIR="$TOOLBOX_DIR/../dot"
TOOLBOX_INSTALL_DIR="$TOOLBOX_DIR/../install"
TOOLBOX_LIB_DIR="$TOOLBOX_DIR/../lib"
TOOLBOX_SECRET_DIR="$TOOLBOX_DIR/../secret"

# ensures we're only appending our LINE if it doesn't already in FILE
LINE=''
FILE=''
grep -qF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"
