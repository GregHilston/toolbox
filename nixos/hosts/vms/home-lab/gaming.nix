{
  config,
  lib,
  pkgs,
  ...
}: let
  cfg = config.gaming;
in {
  options.gaming = {
    enable = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Enable gaming module";
    };
  };

  config = lib.mkIf cfg.enable {
    environment.systemPackages = with pkgs; [
      mangohud # Performance monitoring overlay for games
      lutris # Game manager for Linux
    ];

    programs.gamescope = {
      enable = true;
      capSysNice = true;
      args =
        # The --rt (realtime scheduling) argument is generally beneficial for performance
        # regardless of the display server, so it's always included.
        ["--rt" "--expose-wayland"];
      # For x11 use "--x11-specific-arg" instead of "--expose-wayland" above
    };

    programs.steam = {
      enable = true;
      remotePlay.openFirewall = true;
      dedicatedServer.openFirewall = true;
      gamescopeSession.enable = true;
      localNetworkGameTransfers.openFirewall = true;
    };
  };
}
