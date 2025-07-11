{
  pkgs,
  lib,
  ...
}: {
  programs.swaylock = {
    enable = true;
    package = pkgs.swaylock-effects;

    settings = {
      image = "/nix/store/mny5r8i9v428s08phz3nfh0s04awzd8x-a-house-in-the-snow.png";

      clock = true;
      timestr = "%T";
      datestr = "%F";

      indicator = true;
      indicator-radius = 100;
      indicator-thickness = 7;

      effect-blur = "7x5";
      effect-vignette = "0.5:0.5";

      text-color = "CDD6F4";
      text-clear-color = "CDD6F4";
      text-caps-lock-color = "CDD6F4";
      text-ver-color = "CDD6F4";
      text-wrong-color = "CDD6F4";

      inside-color = lib.mkDefault "1E1E2EEE";
      inside-clear-color = lib.mkDefault "1E1E2EEE";
      inside-caps-lock-color = lib.mkDefault "1E1E2EEE";
      inside-ver-color = lib.mkDefault "1E1E2EEE";
      inside-wrong-color = lib.mkDefault "1E1E2EEE";

      ring-color = "CBA6F7";
      ring-clear-color = "FAB387";
      ring-caps-lock-color = "F5C2E7";
      ring-ver-color = "89B4Fa";
      ring-wrong-color = "F38BA8";

      key-hl-color = "A6E3A1";
      bs-hl-color = "F38BA8";
    };
  };

  # catppuccin.swaylock.enable = false;
}
