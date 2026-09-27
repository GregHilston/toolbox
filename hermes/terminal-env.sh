# Sourced before every Hermes terminal session (config.yaml: terminal.shell_init_files).
# The launchd gateway has no $SHELL, so Hermes runs a bash login shell, which never
# reads .zshrc: without this, every toolbox script is "command not found".
export PATH="$HOME/Git/toolbox/bin:$PATH"
