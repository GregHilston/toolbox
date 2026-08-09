# nixos/modules/programs/tui/zoxide/default.nix
#
# Installs zoxide. The `z` command is wired up in ../zsh — see that module's
# header for why shell integration is centralised there.
_: {
  programs.zoxide.enable = true;
}
