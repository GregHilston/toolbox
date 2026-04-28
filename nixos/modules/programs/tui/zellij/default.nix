# nixos/modules/programs/tui/zellij/default.nix
{...}: {
  programs.zellij = {
    enable = true;
    enableZshIntegration = false; # Don't auto-attach; use manually alongside tmux
  };
}
