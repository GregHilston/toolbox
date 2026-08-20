_: {
  user = {
    # The *local* account name on the machine being built. citadel (work)
    # overrides this to "greghilston". Note this is deliberately not the same
    # concept as the remote login for a host in networking.hosts below — see
    # the `user` field there.
    name = "ghilston";
    fullName = "Greg Hilston";
    email = "Gregory.Hilston@gmail.com";
    packages = {
      # Consumed by modules/common/core.nix and modules/darwin/common.nix to set
      # the login shell. `terminal` and `editor` used to sit here too, but
      # nothing ever read them — the terminal is a stylix-themed programs/gui
      # module and EDITOR is exported from the zsh module.
      shell = "zsh";
    };
  };

  paths = {
    nixosFlake = "$HOME/Git/toolbox/nixos";
  };

  system = {
    timeZone = "America/New_York";
    locale = "en_US.UTF-8";
  };

  services = {
    healthchecks = {
      pingUrl = "https://hc-ping.com/5a471311-5c65-456c-82da-47600e20f1b1";
      intervalSeconds = 300; # 5 minutes
    };
  };

  # Reachable machines on the network. Each entry carries the addresses we know
  # it by plus `user`: the account to log in as *on that machine*. That is a
  # fact about the remote host, not about whoever is building this config —
  # keeping them separate is why citadel's local "greghilston" account no
  # longer leaks into the ssh blocks for the personal machines.
  # Entries without a `user` are not ssh targets.
  networking = {
    hosts = {
      unraid = {
        lan = "192.168.1.2";
        tailscale = "100.102.202.124";
        user = "root";
      };
      pihole1 = {
        lan = "192.168.1.3";
      };
      pihole2 = {
        lan = "192.168.1.4";
      };
      proxmox = {
        lan = "192.168.1.123";
      };
      home-server = {
        lan = "192.168.1.124";
        tailscale = "100.82.90.148";
        user = "ghilston";
      };
      dungeon = {
        # DHCP, so this drifts (was .229, now .238) and `ssh dungeon` breaks
        # until it is re-pinned here while `ssh dungeonts` keeps working. This
        # is the **USB Ethernet** (en7) address — the wired default route, and
        # what `dungeon.local` resolves to. The box also holds a Wi-Fi (en0)
        # address on the same subnet; prefer the wired one.
        # To stop the drift for good, add a DHCP reservation on the router for
        # en7's MAC 00:e0:4c:06:0f:50.
        lan = "192.168.1.238";
        tailscale = "100.103.22.125";
        user = "ghilston";
      };
      moria = {
        # LAN Mac (M4 Max, oMLX + PI WEB server) reached via mDNS/Bonjour — no
        # pinned static IP, so the .local name lives in the `lan` slot.
        # ssh.nix references vars.networking.hosts.moria.lan.
        lan = "moria.local";
        # Tailnet address, stable in a way the DHCP lease is not. This is the
        # address PI WEB binds to and the one home-lab's Caddy on dungeon
        # reverse-proxies pi.grehg2.xyz to — mDNS does not resolve from inside
        # a container, and the LAN lease drifts.
        tailscale = "100.115.155.85";
        user = "ghilston";
      };
      mines = {
        # Pinned via a VMware NAT DHCP reservation on the host (moria):
        # /Library/Preferences/VMware Fusion/vmnet8/dhcpd.conf maps the VM's MAC
        # (00:0c:29:89:17:27) to this fixed-address (outside the .128–.254 dynamic
        # pool), so the lease no longer drifts. See nixos/CLAUDE.md → VMware Fusion.
        lan = "192.168.180.10";
        user = "ghilston";
      };
      fob = {
        tailscale = "100.98.200.16";
        user = "pi";
      };
      rohan = {
        lan = "192.168.1.222";
        user = "ghilston";
      };
      pixel = {
        lan = "192.168.1.201";
        user = "u0_a305";
        sshPort = 8022; # Termux sshd
      };
    };
  };
}
