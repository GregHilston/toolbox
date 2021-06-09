#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

echo "Installing oh my zsh..."


sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended

# this is required because passing the --unattended flag does not prompt
# for changing the shell
echo "Changing default shell to be zsh..."
chsh -s $(which zsh)

printf "⚠️  There may be above errors that would be caused by running toolbox Makefile more than once and can be safely ignored..."

# required if we want to rerun makefile, the above script fails. I want to avoid that
exit 0
