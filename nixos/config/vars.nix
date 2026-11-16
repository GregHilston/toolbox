_: {
  user = {
    # The *local* account name on the machine being built. citadel (work)
    # overrides this to "greghilston". Note this is deliberately not the same
    # concept as the remote login for a host in networking.hosts below — see
    # the `user` field there.
    name = "ghilston";
    fullName = "Greg Hilston";
    email = "Gregory.Hilston@gmail.com";
    # Public keys allowed to log in as this user, on NixOS and darwin alike.
    authorizedKeys = [
      "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCmEoG6aAA559ZIVc4citslV5TxVTb3tbheaSTB/+bo1uOi/IDVS/yEgDqObY2KvP7uqeNqn10diVoe0Pg4yLiFTuNriFA6aPmhs00DjazttGj8WyFDOJnBIg1NL9BlewvkxlSXa/LsWfN8JanZ1Cwknff8jxxbm+s1CxV8+XWWK4MHsfHixfD69UP437cJ9QuomKFrWZ4A+s4SUHfKVknFn0xDgclay3/h6cAdc9+rlYe73UY6AzeqgKlOxL1S1NNn2TIyhmBQm32xhsW++LLpG/4jv1+pgRHeghmJYPk1+ZeGkGRi/oRSibMActa960WBccHOMxCTVDhF/Rkyw4RoMCU/gU3zFY8Nm92xM34+SU23Sf1xdP6Gs2/raQIf49bVOkGNZXtmHBh+dvnTBxmgXcyHHoJGLPYy/Ct/IYYoeRn6lRxiBSidu0kk9hwL0JqF75a7wDlHXN4hWLXvma4RKrIgGt8pJGsjjIa1bWSKKUowuLgm56PCDC0Dxa95fBE= moria (macbook pro)"
      "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDH+/1isYqdcDmQ9S3crcezjCfqRc4mIgxF3dYfbjYBmsfnEcd/hCujfcmJMJTyQ1ZMyGyOCk+3B2P2D3HxB7OJg74qnUya9Wfwza3O6v+l6Gttu02bZ3eV16lKgrqUm+mpD3bxlbhvmFGEQKbAuy+EB9kTQKm1FM2vaeWr76B43U/9ToFJYsns29gTRaeKYTFzm5F3n1Rl2dKJrL7YhT+h9GnQ9cTzbzYFmyctIh6lLvHAOszHxow07ybuBwEzqbAALcslUzvjkx2TDTUmsaEysxFWHPMCvsiiBWow12e84nMeHcq1pazNLHptLuSh7ziRYhQ1gWNsbe5FKd33Ac5S06U7QHF+VjpfYahmFO40XGJLMOwyFTbWFGpiT6pl8alfOjwp7f4oiq+jqHvSAl0xjLjogZNajWiaKc6kS0a14BtnD9c34kglVIbo50EpNvG7O5FVcZhxxAqWgZgQJrQWqklsucL4s5yBDyjln4u52441C+TC1tpDxaq2VRWeA7c= citadel"
      "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCgza0/oRd+XKbP1SmGBwlkYh4T2NPk8nlb/XsHvlMow4ItEsu9C4Dvo+ueLAhI7+pOYTLwdTdgA+mR5Abqp8hfzQnElLiGT5/GF+RB7V8E7X/U0H3ypL/iTdu/NqRtbaPQdaApxqaMeiIn3LLDR8PJqhYFSoSGveodC7NghNNMFtw8odHy38PyjGZjgSbVwUAtDTQjlz2opqk2l81eGpcplLzJWSuqYkGIAAhVxngq9bbBYteNukfY2f0dD2VEWvyybAPOkCZxk7oIAjQD7eyzmJl40giO7+8cTNxmts01+lV4DmZa1xRFfNFbMc8rLErOZJx+V6ANvzlCNb4ltkEaqTyhYXhhoLiIYW2pmI8c20iSdmwJ6hhfaK4MvOVPGpW5X05ZcBkVxO+rMe+PkM2T25JQyvIOMFS2EaP1oFNBiMQwhHv3KT529kvHjtmCXumsjV/pC/hIuhef/so7dEHFmzyl72gQ5EWSMQ5ijmhlQM0uP+c7DIM2LBnwEBKVYZU= foundation"
    ];
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
    # MagicDNS suffix: <tailscale node name>.<tailnet>.
    tailnet = "tail1b9d9.ts.net";
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
        # mDNS, because the DHCP lease drifts.
        lan = "dungeon.local";
        tailscale = "100.103.22.125";
        user = "ghilston";
      };
      moria = {
        # LAN Mac (M4 Max, oMLX + PI WEB server) reached via mDNS/Bonjour — no
        # pinned static IP, so the .local name lives in the `lan` slot.
        lan = "moria.local";
        # Tailnet address, stable in a way the DHCP lease is not. This is the
        # address PI WEB binds to and the one home-lab's Caddy on dungeon
        # reverse-proxies pi.grehg2.xyz to — mDNS does not resolve from inside
        # a container, and the LAN lease drifts.
        tailscale = "100.115.155.85";
        user = "ghilston";
      };
      citadel = {
        lan = "citadel.local";
        tailscale = "100.93.190.106";
        # specifically NOT ghilston
        user = "greghilston";
      };
      foundation = {
        # Windows' own mDNS name; WSL has none.
        lan = "DESKTOP-1IMUF2A.local";
        tailscale = "100.80.240.26";
        user = "ghilston";
        sshPort = 2222; # Windows portproxy into WSL
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
