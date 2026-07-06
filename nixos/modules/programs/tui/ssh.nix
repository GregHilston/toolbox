{vars, ...}: {
  programs.ssh = {
    enable = true;
    enableDefaultConfig = false;

    matchBlocks = {
      "github.com" = {
        hostname = "github.com";
        user = "git";
        identityFile = "~/.ssh/id_rsa";
      };
      "unraid" = {
        hostname = vars.networking.hosts.unraid.tailscale;
        user = "root";
        identityFile = "~/.ssh/id_rsa";
      };
      "home-server" = {
        hostname = vars.networking.hosts.home-server.tailscale;
        user = vars.user.name;
        identityFile = "~/.ssh/id_rsa";
      };
      "dungeon" = {
        hostname = vars.networking.hosts.dungeon.lan;
        user = vars.user.name;
        identityFile = "~/.ssh/id_rsa";
      };
      "dungeonts" = {
        hostname = vars.networking.hosts.dungeon.tailscale;
        user = vars.user.name;
        identityFile = "~/.ssh/id_rsa";
      };
      "moria" = {
        hostname = vars.networking.hosts.moria.lan;
        # Hardcoded (not vars.user.name): moria's account is always "ghilston",
        # whereas on the work host citadel vars.user.name is "greghilston" —
        # which would be the wrong remote user for moria.
        user = "ghilston";
        identityFile = "~/.ssh/id_rsa";
      };
      "mines" = {
        hostname = vars.networking.hosts.mines.lan;
        user = vars.user.name;
        identityFile = "~/.ssh/id_rsa";
        extraOptions = {
          IdentitiesOnly = "yes";
          ForwardAgent = "yes";
        };
      };
      "rohan" = {
        hostname = vars.networking.hosts.rohan.lan;
        user = vars.user.name;
        identityFile = "~/.ssh/id_rsa";
      };
      "fob" = {
        hostname = vars.networking.hosts.fob.tailscale;
        user = "pi";
        identityFile = "~/.ssh/id_rsa";
      };
      "pixel" = {
        hostname = vars.networking.hosts.pixel.lan;
        user = "u0_a305";
        port = 8022;
        identityFile = "~/.ssh/id_rsa";
      };
      "*" = {
        identityFile = "~/.ssh/id_rsa";
      };
    };
  };
}
