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

  # The Pixel's keys: Herdr app, then Termux.
  users.users.${vars.user.name}.openssh.authorizedKeys.keys = [
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEi4FZc245nOdNzPYKSB7tRczEpApiiVlFWUr57w1TVI herdr-mobile"
    "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCWQLGTzFnal+22+gs8mfvgXKpafO7SPvl3loiQ+O9M+TX8CvNNyMoksfbxVq73h/mRBqdzYkRxIIYGvIRBIrpbLjM3bwqa/jZqvVliohrmJdhPP6xDc5J4qbwc4Qr8atHxYAN0f8JiW3D68wipcgbNdZs2b/V9qA1JXMMOvZEEGYYmMqCbXxFJTOmbAnELxy8qon/D98N5BAy3FpD/WFl4CGfdeU5G4mhX6fM68fc1WbMIwcwJRRwU5F/jA3PrvkhapO3xaCSVSxd4JxV1EaQ+6D1Ru9JjWNk2Objas7CMz+N6eSd699LFAmFxoA9FUGOBY8iupdvbci9BA4GXsN2ZfhYOACMQoaNyLsqf/LnFHXluA8ALe0DPatfznyKD7fltDyYf5GDLlTybg2a5GebUFCHkiLptLW2I94eBil3L6kH+MCnZHPiHCzkeObs1Brd4T/yi18G6n+cvUD8zvL/5BqB4YUxtBR2eqOVWZpUpeEbp8mEtbZUe/CZZd6Bg+J8= pixel 8"
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
