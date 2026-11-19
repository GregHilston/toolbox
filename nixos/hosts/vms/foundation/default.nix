{
  lib,
  vars,
  ...
}: {
  imports = [
    ../../../modules/common
  ];

  networking.hostName = "foundation";
  services.openssh.enable = true;

  # The Herdr phone app's key.
  users.users.${vars.user.name}.openssh.authorizedKeys.keys = [
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEi4FZc245nOdNzPYKSB7tRczEpApiiVlFWUr57w1TVI herdr-mobile"
  ];

  # WSL has no kernel links; reboot check aborts.
  system.autoUpgrade.allowReboot = lib.mkForce false;

  # The primary user (groups, password, shell, ssh key) comes from
  # modules/common/core.nix, with input/docker added by modules/common.

  # Desktop is off here simply by not setting custom.desktop.enable, so the KDE
  # stack (xserver/sddm/plasma6/pipewire/rtkit/1Password GUI) and the GUI home
  # packages are never enabled — no per-service overrides needed.

  # Disable networking services unnecessary in WSL
  networking.wireless.enable = lib.mkForce false; # Disables wpa_supplicant

  # 1Password CLI doesn't work in WSL (needs the desktop app for unlock)
  programs._1password.enable = lib.mkForce false;

  # WSL-specific settings
  wsl = {
    enable = true;
    defaultUser = vars.user.name;
    startMenuLaunchers = true;
    # Links /usr/lib/wsl/lib's CUDA and NVML into /run/opengl-driver.
    useWindowsDriver = true;
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

  # uv's standalone Python misses NixOS's CA bundle.
  environment.variables.SSL_CERT_FILE = "/etc/ssl/certs/ca-certificates.crt";

  # Second orchestrator host (loser-picks #187): pi reaches the LiteLLM
  # gateway, op reads the service-account token from ~/.config/op.
  home-manager.users.${vars.user.name} = {pkgs, ...}: {
    imports = [../../../modules/programs/tui/pi.nix ./gridkeep-tools.nix];
    home.packages = with pkgs; [pi-coding-agent _1password-cli];
    custom.programs.pi = {
      enable = true;
      generateModelsJson = true;
    };
  };
}
