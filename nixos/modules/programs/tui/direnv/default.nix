# nixos/modules/programs/tui/direnv/default.nix
{vars, ...}: {
  programs.direnv = {
    enable = true;
    nix-direnv.enable = true;
    enableZshIntegration = true;
    config.whitelist.prefix = [
      "/Users/${vars.user.name}/Git/home-lab"
      "/Users/${vars.user.name}/Git/toolbox"
    ];
  };
}
