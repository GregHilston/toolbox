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
      "mines" = {
        hostname = vars.networking.hosts.mines.lan;
        user = vars.user.name;
        identityFile = "~/.ssh/id_rsa";
        extraOptions = {
          IdentitiesOnly = "yes";
          ForwardAgent = "yes";
        };
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
