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
{
  lib,
  vars,
  ...
}: let
  inherit (vars.networking) hosts tailnet;
  # Names, not IPs: leases drift, nodes re-register.
  meshHost = name: let
    h = hosts.${name};
    common = {User = h.user;} // lib.optionalAttrs (h ? sshPort) {Port = h.sshPort;};
  in {
    ${name} = common // {HostName = h.lan;};
    "${name}ts" = common // {HostName = "${name}.${tailnet}";};
  };
  mesh = lib.mergeAttrsList (map meshHost ["moria" "dungeon" "citadel" "foundation"]);
in {
  programs.ssh = {
    enable = true;
    enableDefaultConfig = false;

    settings =
      mesh
      // {
        "github.com" = {
          HostName = "github.com";
          User = "git";
        };
        "unraid" = {
          HostName = hosts.unraid.lan;
          User = hosts.unraid.user;
        };
        "unraidts" = {
          HostName = hosts.unraid.tailscale;
          User = hosts.unraid.user;
        };
        "home-server" = {
          HostName = hosts.home-server.tailscale;
          User = hosts.home-server.user;
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
        # Hetzner VPS: debrief, and Gridkeep prod (#616).
        "debrief" = {
          HostName = "178.105.216.204";
          User = "root";
          IdentityFile = "\"~/.ssh/foo hetzner server\"";
          IdentitiesOnly = true;
        };
        "*" = {
          IdentityFile = "~/.ssh/id_rsa";
        };
      };
  };
}
