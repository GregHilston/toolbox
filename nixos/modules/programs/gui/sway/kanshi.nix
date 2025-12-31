{
  pkgs,
  config,
  lib,
  ...
}: let
  inherit (lib) mkIf mkEnableOption;
  cfg = config.ghilston.opt.services.kanshi;
in {
  options.ghilston.opt.services.kanshi.enable = mkEnableOption "kanshi";

  config = mkIf cfg.enable {
    home = {
      packages = with pkgs; [kanshi];
    };
    services.kanshi = {
      enable = true;
      # systemdTarget = "sway-session.target";
      settings = [
        {
          profile.name = "universal";
          profile.outputs = [
            {
              criteria = "*";
              # Optionally specify mode, scale, etc., if you want defaults for all monitors
              # mode = "1920x1080@60";
              # position = "0,0";
              # scale = 1.0;
              status = "enable";
            }
          ];
        }
      ];
    };
  };
}
