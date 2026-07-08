{
  inputs,
  outputs,
  lib,
  config,
  pkgs,
  vars,
  ...
}: let
  basePackages = import ../../config/base-packages.nix pkgs;
in {
  imports = [
    ./core.nix
    ../../modules/stylix
  ];

  system.autoUpgrade = {
    enable = true;
    allowReboot = true;
  };

  home-manager = {
    extraSpecialArgs = {
      inherit inputs outputs vars;
    };
    users.${vars.user.name} = import ../../modules/home;
  };

  # nixpkgs overlays + allowUnfree come from the shared nixpkgsModule in
  # flake-modules/hosts.nix. nix settings, networking, locale, and the base
  # user (groups networkmanager + wheel) come from ./core.nix.

  # Allows using nix-ld to run dynamically linked ELF binaries
  # from Nix store without needing to build a fully static binary.
  # For example, this will allow VSCode server to run properly.
  programs.nix-ld.enable = true;

  # Docker-Compose
  virtualisation = {
    libvirtd.enable = false;
    docker.enable = true;
    podman.enable = false;
  };
  programs = {
    virt-manager.enable = false;

    # 1Password system integration
    # Enables CLI integration and browser extension support
    # Browser integration automatically works for Firefox, Chrome, and Brave
    _1password.enable = true;
    _1password-gui = {
      enable = true;
      polkitPolicyOwners = [vars.user.name];
    };
  };

  services = {
    xserver.enable = true;
    displayManager.sddm.enable = true;
    desktopManager.plasma6.enable = true;

    xserver.xkb = {
      layout = "us";
      variant = "";
    };

    pipewire = {
      enable = true;
      alsa.enable = true;
      alsa.support32Bit = true;
      pulse.enable = true;
    };
  };

  security.rtkit.enable = true;

  # Top up the base user (defined in ./core.nix) with desktop/docker groups.
  users.users.${vars.user.name}.extraGroups = ["input" "docker"];

  environment = {
    # Shared baseline (config/base-packages.nix) plus NixOS-only extras.
    # Darwin gets just/stow/gh via Homebrew, so they live here, not in the base.
    # Note: xclip lives in home.packages behind the enableGui conditional so
    # GUI systems get a clipboard while WSL doesn't.
    systemPackages =
      basePackages.systemPackages
      ++ (with pkgs; [
        tmux
        fastfetch
        just
        stow
        python3
        pandoc
        gh
      ]);

    sessionVariables = {
      EDITOR = "nvim";
    };
  };

  system.stateVersion = "24.05";
}
