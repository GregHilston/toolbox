# nixos/modules/programs/tui/fzf/default.nix
#
# Installs fzf. The keybindings (Ctrl+T / Ctrl+R / Alt+C) and FZF_DEFAULT_*
# environment are set in ../zsh — see that module's header for why shell
# integration is centralised there. In particular `programs.fzf.defaultCommand`
# and `defaultOptions` only reach the shell via home.sessionVariables, which
# nothing sources here, so they are set as plain exports in .zshrc.local instead.
_: {
  programs.fzf.enable = true;
}
