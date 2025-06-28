{
  inputs,
  outputs,
  lib,
  config,
  pkgs,
  vars,
  ...
}: {
  imports = [
    ../../../modules/common
  ];

  networking.hostName = "foundation";

  # Ensure both users exist during transition
  users.users = {
    nixos = {
      isNormalUser = true;
      extraGroups = ["wheel" "networkmanager"];
      # Keep nixos user temporarily
    };
    ${vars.user.name} = {
      isNormalUser = true;
      extraGroups = ["wheel" "networkmanager" "docker"];
      initialPassword = "password";
    };
  };

  # Override common settings that don't work well in WSL
  services = {
    xserver.enable = lib.mkForce false;
    displayManager.sddm.enable = lib.mkForce false;
    desktopManager.plasma6.enable = lib.mkForce false;
    pipewire.enable = lib.mkForce false;
  };

  # Disable unnecessary services for WSL
  security.rtkit.enable = lib.mkOverride 900 false;
  virtualisation.docker.enable = true;

  # WSL-specific settings
  wsl = {
    enable = true;
    defaultUser = vars.user.name;
    startMenuLaunchers = true;
    wslConf = {
      automount.root = "/mnt";
      network.generateResolvConf = true;
    };
  };

  # Disable Stylix desktop-related targets
  stylix = {
    targets.console.enable = false;
  };

  # Configure home-manager for WSL
  home-manager = {
    extraSpecialArgs = {
      inherit inputs outputs vars;
    };
    users.${vars.user.name} = {pkgs, ...}: {
      imports = [../../../modules/home];
    };
  };
}
