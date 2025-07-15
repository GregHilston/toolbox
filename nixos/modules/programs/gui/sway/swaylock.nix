{
  pkgs,
  lib,
  ...
}: {
  programs.swaylock = {
    enable = true;
    package = pkgs.swaylock-effects;

    settings = {
      screenshots = true;
      daemonize = true;
      ignore-empty-password = true;
      clock = true;
      indicator = true;
      effect-blur = "10x5";
      effect-vignette = "0.5:1";
    };
  };

  # catppuccin.swaylock.enable = false;
}
