#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# from https://www.git-tower.com/learn/git/faq/change-author-name-email/

git filter-branch --env-filter '
declare -a WRONG_NAMES=("GregHilstonHop" "Greg Hilston")
NEW_NAME="GregHilston"

for i in "${WRONG_NAMES[@]}"
do
    if [ "$GIT_COMMITTER_NAME" != "$i" ]
    then
        export GIT_COMMITTER_NAME="$NEW_NAME"
    fi
done
' --tag-name-filter cat -- --branches --tags