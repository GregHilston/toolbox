{
  lib,
  config,
  pkgs,
  vars,
  ...
}: let
  cfg = config.custom.nh;
in {
  options.custom.nh = {
    enable = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Enable the nh module";
    };
    flake = lib.mkOption {
      type = lib.types.str;
      default = vars.paths.nixosFlake;
      description = "Path to the flake.nix file.";
    };
  };

  config = lib.mkIf cfg.enable {
    programs.nh = {
      enable = true;
      inherit (cfg) flake; # Use the option here
    };
    home.packages = with pkgs; [
      nix-output-monitor
      nvd
    ];
  };
}
