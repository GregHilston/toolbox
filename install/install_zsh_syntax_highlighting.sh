
#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

echo "Installing ZSH syntax highlighting..."
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git $ZSH_CUSTOM/plugins/zsh-syntax-highlighting