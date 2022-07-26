#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# from https://gist.github.com/jen20/218642f3c2cd0e2ce8b6b95ca59e0538

echo "Installing latest Jetbrains Toolbox"

if [[ ! -f ~/.local/share/JetBrains/Toolbox/bin/jetbrains-toolbox ]]; then
  URL=$(curl -s 'https://data.services.jetbrains.com//products/releases?code=TBA&latest=true&type=release' | jq -r '.TBA[0].downloads.linux.link')

  DOWNLOAD_TEMP_DIR=$(mktemp -d)

  mkdir -p "${DOWNLOAD_TEMP_DIR}"

  curl -L "${URL}" --output "${DOWNLOAD_TEMP_DIR}/toolbox.tar.gz"

  TOOLBOX_TEMP_DIR=$(mktemp -d)

  tar -C "$TOOLBOX_TEMP_DIR" -xf "${DOWNLOAD_TEMP_DIR}/toolbox.tar.gz"
  rm "${DOWNLOAD_TEMP_DIR}/toolbox.tar.gz"

  # for whatever stupid reasons bash doesn't expand the star here...
  # it automatically installs itself into ~/.local/share/JetBrains/Toolbox/
  bash -c "${TOOLBOX_TEMP_DIR}/*/jetbrains-toolbox"
  rm -rf "${TOOLBOX_TEMP_DIR}"
  echo "Installing jetbrains Toolbox: done."
fi
