{ config, pkgs, ... }:
let
  user = "ghilston"; # TODO have this get passed in somehow
in
{
  # hardware.graphics = {
  #   enable = true;
  #   enable32Bit = true;
  # };

  # TODO have some useNvidia variable get passed in to turn this on or off
  # services.xserver.videoDrivers = ["nvidia"];
  # hardware.nvidia.modesetting.enable = true;

  # environment.systemPackages = with pkgs; [
  #   mangohud
  # ];

  programs.steam = {
    enable = true;
    # useNativeRuntime = true;
    # gamescopeSession.enable = true;
    remotePlay.openFirewall = true; # Open ports in the firewall for Steam Remote Play
    dedicatedServer.openFirewall = true; # Open ports in the firewall for Source Dedicated Server
  };

  home-manager.users.${user} = {
    home.stateVersion = "24.05";

    home.packages = with pkgs; [
      steam-tui
      steamcmd
    ];

    programs.bash = {
      enable = true;
      shellAliases = {
        "steam-tui" = "${pkgs.steam-tui}/bin/steam-tui";
        "steamcmd" = "${pkgs.steamcmd}/bin/steamcmd";
      };
    };
    # programs.gamemode.enable = true;
  };
}

# Can prepend one of the following launch options to any steam game
# gamemoderun %command%
# mangohud %command%
# gamescope %command%