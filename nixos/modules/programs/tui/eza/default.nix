# nixos/modules/programs/tui/eza/default.nix
#
# Installs eza. The `ls`/`ll`/`la`/… aliases and their flags live in ../zsh —
# see that module's header for why shell integration is centralised there.
_: {
  programs.eza.enable = true;
}
