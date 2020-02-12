#!/bin/bash
# github.sh
# When run within a git repository with a remote hosted on GitHub, opens the project on GitHub's web interface in the
# default browser
​
githubUrl=$(git remote get-url --push origin | grep github.com)
​
if [ -n "$githubUrl" ]; then
  fullUrl="https://github.com/$(perl -pe 's/.*@github\.com.(.*)\.git/\1/' <<< "$githubUrl")"
  if ! x-www-browser "$fullUrl"; then
    open "$fullUrl"
  fi
else
  echo 'No github remote'
  exit 1
fi
