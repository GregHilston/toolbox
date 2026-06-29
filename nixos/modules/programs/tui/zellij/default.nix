# nixos/modules/programs/tui/zellij/default.nix
_: {
  programs.zellij = {
    enable = true;
    enableZshIntegration = false; # Don't auto-attach; use manually alongside tmux
  };
}
