# nixos/modules/programs/tui/direnv/default.nix
{config, ...}: {
  programs.direnv = {
    enable = true;
    nix-direnv.enable = true;
    # The `direnv hook zsh` eval lives in the portable dot/zsh/.zshrc (it works
    # on non-nix machines too). `config.whitelist` below is real config — it
    # renders ~/.config/direnv/direnv.toml.
    #
    # Use the platform-correct home dir (config.home.homeDirectory): /home/<user>
    # on NixOS, /Users/<user> on Darwin. Hardcoding /Users/... meant the whitelist
    # never matched on NixOS, so direnv didn't auto-allow these repos there.
    config.whitelist.prefix = [
      "${config.home.homeDirectory}/Git/home-lab"
      "${config.home.homeDirectory}/Git/toolbox"
    ];
  };
}
