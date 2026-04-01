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
      };
      mines = {
        lan = "192.168.180.132";
      };
      fob = {
        tailscale = "100.98.200.16";
      };
    };
  };
}
