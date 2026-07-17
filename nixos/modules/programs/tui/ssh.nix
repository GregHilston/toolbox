# SSH client config.
#
# Uses the newer `programs.ssh.settings` schema (home-manager deprecated
# `programs.ssh.matchBlocks`). Each attribute name becomes a `Host <name>` block,
# and the values are OpenSSH directive names verbatim (HostName, User, IdentityFile,
# Port, ForwardAgent, IdentitiesOnly …) — what used to live under `extraOptions` is
# now just more directives in the same block.
{vars, ...}: {
  programs.ssh = {
    enable = true;
    enableDefaultConfig = false;

    settings = {
      "github.com" = {
        HostName = "github.com";
        User = "git";
        IdentityFile = "~/.ssh/id_rsa";
      };
      "unraid" = {
        HostName = vars.networking.hosts.unraid.tailscale;
        User = "root";
        IdentityFile = "~/.ssh/id_rsa";
      };
      "home-server" = {
        HostName = vars.networking.hosts.home-server.tailscale;
        User = vars.user.name;
        IdentityFile = "~/.ssh/id_rsa";
      };
      "dungeon" = {
        HostName = vars.networking.hosts.dungeon.lan;
        User = vars.user.name;
        IdentityFile = "~/.ssh/id_rsa";
      };
      "dungeonts" = {
        HostName = vars.networking.hosts.dungeon.tailscale;
        User = vars.user.name;
        IdentityFile = "~/.ssh/id_rsa";
      };
      "moria" = {
        HostName = vars.networking.hosts.moria.lan;
        # Hardcoded (not vars.user.name): moria's account is always "ghilston",
        # whereas on the work host citadel vars.user.name is "greghilston" —
        # which would be the wrong remote user for moria.
        User = "ghilston";
        IdentityFile = "~/.ssh/id_rsa";
      };
      "mines" = {
        HostName = vars.networking.hosts.mines.lan;
        User = vars.user.name;
        IdentityFile = "~/.ssh/id_rsa";
        IdentitiesOnly = true;
        ForwardAgent = true;
      };
      "rohan" = {
        HostName = vars.networking.hosts.rohan.lan;
        User = vars.user.name;
        IdentityFile = "~/.ssh/id_rsa";
      };
      "fob" = {
        HostName = vars.networking.hosts.fob.tailscale;
        User = "pi";
        IdentityFile = "~/.ssh/id_rsa";
      };
      "pixel" = {
        HostName = vars.networking.hosts.pixel.lan;
        User = "u0_a305";
        Port = 8022;
        IdentityFile = "~/.ssh/id_rsa";
      };
      "*" = {
        IdentityFile = "~/.ssh/id_rsa";
      };
    };
  };
}
