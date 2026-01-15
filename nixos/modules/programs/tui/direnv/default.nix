# nixos/modules/programs/tui/direnv/default.nix
{...}: {
  programs.direnv = {
    enable = true;
    nix-direnv.enable = true;
    enableZshIntegration = true;
  };
}
