{lib, ...}: rec {
  user = {
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

  networking = {
    domain = "local";
    hosts = {
      unraid = {
        lan = "192.168.1.2";
        tailscale = "100.102.202.124";
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
      };
      dungeon = {
        lan = "192.168.1.174";
        tailscale = "100.103.22.125";
      };
      moria = {
        # LAN Mac (M4 Max, oMLX server) reached via mDNS/Bonjour — no pinned
        # static IP, so the .local name lives in the `lan` slot. Swap in an IP
        # or add a `tailscale` entry later if desired; ssh.nix references
        # vars.networking.hosts.moria.lan.
        lan = "moria.local";
      };
      mines = {
        # Pinned via a VMware NAT DHCP reservation on the host (moria):
        # /Library/Preferences/VMware Fusion/vmnet8/dhcpd.conf maps the VM's MAC
        # (00:0c:29:89:17:27) to this fixed-address (outside the .128–.254 dynamic
        # pool), so the lease no longer drifts. See nixos/CLAUDE.md → VMware Fusion.
        lan = "192.168.180.10";
      };
      fob = {
        tailscale = "100.98.200.16";
      };
      rohan = {
        lan = "192.168.1.222";
      };
      pixel = {
        lan = "192.168.1.201";
      };
    };
  };
}
