#!/usr/bin/env bash
set -e

# Work in progress

TOOLBOX_DIR="$PWD"
TOOLBOX_BIN_DIR="$TOOLBOX_DIR/../bin"
TOOLBOX_DOTS_DIR="$TOOLBOX_DIR/../dots"
TOOLBOX_INSTALL_DIR="$TOOLBOX_DIR/../install"
TOOLBOX_LIB_DIR="$TOOLBOX_DIR/../lib"
TOOLBOX_SECRETS_DIR="$TOOLBOX_DIR/../secrets"

# ensures we're only appending our LINE if it doesn't already in FILE
LINE=''
FILE=''
grep -qF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"