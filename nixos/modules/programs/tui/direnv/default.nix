# nixos/modules/programs/tui/direnv/default.nix
{config, lib, ...}: {
  programs.direnv = {
    enable = true;
    nix-direnv.enable = true;
    enableZshIntegration = true;
  };
}
