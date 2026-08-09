# SSH client config.
#
# Uses the newer `programs.ssh.settings` schema (home-manager deprecated
# `programs.ssh.matchBlocks`). Each attribute name becomes a `Host <name>` block,
# and the values are OpenSSH directive names verbatim (HostName, User, IdentityFile,
# Port, ForwardAgent, IdentitiesOnly …) — what used to live under `extraOptions` is
# now just more directives in the same block.
#
# Two things keep this table short:
#   * The remote login lives in config/vars.nix next to the host's addresses
#     (`hosts.<name>.user`), because it describes the *remote* machine. It used
#     to be `vars.user.name`, which is the *local* account and is "greghilston"
#     on the work laptop — wrong for every personal box, which is why moria
#     needed a hardcoded exception.
#   * IdentityFile is set once in the `Host *` block, which OpenSSH applies to
#     every host. Repeating it per block bought nothing.
{vars, ...}: let
  inherit (vars.networking) hosts;
in {
  programs.ssh = {
    enable = true;
    enableDefaultConfig = false;

    settings = {
      "github.com" = {
        HostName = "github.com";
        User = "git";
      };
      "unraid" = {
        HostName = hosts.unraid.tailscale;
        User = hosts.unraid.user;
      };
      "home-server" = {
        HostName = hosts.home-server.tailscale;
        User = hosts.home-server.user;
      };
      "dungeon" = {
        HostName = hosts.dungeon.lan;
        User = hosts.dungeon.user;
      };
      "dungeonts" = {
        HostName = hosts.dungeon.tailscale;
        User = hosts.dungeon.user;
      };
      "moria" = {
        HostName = hosts.moria.lan;
        User = hosts.moria.user;
      };
      "mines" = {
        HostName = hosts.mines.lan;
        User = hosts.mines.user;
        # Agent forwarding so the VM can reach GitHub with the host's key.
        IdentitiesOnly = true;
        ForwardAgent = true;
      };
      "rohan" = {
        HostName = hosts.rohan.lan;
        User = hosts.rohan.user;
      };
      "fob" = {
        HostName = hosts.fob.tailscale;
        User = hosts.fob.user;
      };
      "pixel" = {
        HostName = hosts.pixel.lan;
        User = hosts.pixel.user;
        Port = hosts.pixel.sshPort;
      };
      "*" = {
        IdentityFile = "~/.ssh/id_rsa";
      };
    };
  };
}
