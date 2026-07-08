{
  lib,
  vars,
  ...
}: {
  imports = [
    ../../../modules/common
  ];

  networking.hostName = "foundation";

  users.users.${vars.user.name} = {
    isNormalUser = true;
    extraGroups = ["wheel" "networkmanager" "docker"];
    initialPassword = "password";
  };

  # Desktop is off here via enableGui = false (set in flake-modules/hosts.nix),
  # so the KDE stack (xserver/sddm/plasma6/pipewire/rtkit/1Password GUI) and the
  # GUI home packages are simply never enabled — no per-service overrides needed.

  # Disable networking services unnecessary in WSL
  networking.wireless.enable = lib.mkForce false; # Disables wpa_supplicant

  # 1Password CLI doesn't work in WSL (needs the desktop app for unlock)
  programs._1password.enable = lib.mkForce false;

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

  # Disable Stylix desktop-related targets for WSL
  stylix = {
    targets.console.enable = false;
    targets.plymouth.enable = false; # WSL has no boot splash screen
  };
}
