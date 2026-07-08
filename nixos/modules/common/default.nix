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
    ./desktop.nix
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

    # 1Password system integration (CLI + browser extension support).
    # Browser integration automatically works for Firefox, Chrome, and Brave.
    # The 1Password GUI lives in ./desktop.nix (gated on custom.desktop.enable).
    _1password.enable = true;
  };

  # The KDE Plasma desktop stack (xserver/sddm/plasma6/pipewire/rtkit/1Password
  # GUI) lives in ./desktop.nix, gated on custom.desktop.enable.

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
