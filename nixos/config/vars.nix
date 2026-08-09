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
      terminal = "alacritty";
      editor = "nvim";
      shell = "zsh";
    };
  };

  paths = {
    dotfiles = "$HOME/.dotfiles";
    configHome = "$HOME/.config";
    dataHome = "$HOME/.local/share";
    cacheHome = "$HOME/.cache";
    nixosFlake = "$HOME/Git/toolbox/nixos";
  };

  system = {
    timeZone = "America/New_York";
    locale = "en_US.UTF-8";
    stateVersion = "24.05";
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
    domain = "local";
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
        lan = "192.168.1.229";
        tailscale = "100.103.22.125";
        user = "ghilston";
      };
      moria = {
        # LAN Mac (M4 Max, oMLX server) reached via mDNS/Bonjour — no pinned
        # static IP, so the .local name lives in the `lan` slot. Swap in an IP
        # or add a `tailscale` entry later if desired; ssh.nix references
        # vars.networking.hosts.moria.lan.
        lan = "moria.local";
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
