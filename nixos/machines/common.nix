{ config, pkgs, ... }:

let
  user = "ghilston";
in
{
  # Common imports
  imports =
  [
    ./hardware-configuration.nix
    ../../modules/home
  ];

  # Bootloader
  boot.loader.grub.enable = true;
  boot.loader.grub.device = "/dev/sda";
  boot.loader.grub.useOSProber = true;

  # Networking
  networking.networkmanager.enable = true;
  networking.hostName = "nixos";

  # Set your time zone
  time.timeZone = "America/New_York";

  # Select internationalisation properties
  i18n.defaultLocale = "en_US.UTF-8";
  i18n.extraLocaleSettings = {
    LC_ADDRESS = "en_US.UTF-8";
    LC_IDENTIFICATION = "en_US.UTF-8";
    LC_MEASUREMENT = "en_US.UTF-8";
    LC_MONETARY = "en_US.UTF-8";
    LC_NAME = "en_US.UTF-8";
    LC_NUMERIC = "en_US.UTF-8";
    LC_PAPER = "en_US.UTF-8";
    LC_TELEPHONE = "en_US.UTF-8";
    LC_TIME = "en_US.UTF-8";
  };

  # Enable the X11 windowing system
  services.xserver.enable = true;

  # Enable the KDE Plasma Desktop Environment
  services.displayManager.sddm.enable = true;
  services.desktopManager.plasma6.enable = true;

  # Configure keymap in X11
  services.xserver.xkb = {
    layout = "us";
    variant = "";
  };

  # Enable sound with pipewire
  hardware.pulseaudio.enable = false;
  security.rtkit.enable = true;
  services.pipewire = {
    enable = true;
    alsa.enable = true;
    alsa.support32Bit = true;
    pulse.enable = true;
  };

  # Enable zsh as the main shell
  programs.zsh.enable = true;
  users.defaultUserShell = pkgs.zsh;

  # Install useful system-wide packages
  environment.systemPackages = with pkgs; [
    zsh
    tmux
    file
    git
    htop
    jq
    rsync
    tldr
    neovim
    vimPlugins.vim-plug
    unzip
    wget
    curl
    zip
    neofetch
    tree
    ncdu
    just
  ];

  # Set session variables
  environment.sessionVariables = {
      EDITOR = "nvim";
  };

  # Enable Firefox
  programs.firefox.enable = true;

  # Enable unfree packages
  nixpkgs.config.allowUnfree = true;

  # OpenSSH service
  services.openssh.enable = true;
  services.openssh.settings.X11Forwarding = true;

  # User configuration
  users.users = {
    ghilston = {
      isNormalUser = true;
      extraGroups = [ "networkmanager" "wheel" "docker" ];
    };
  };

  # Enable Docker
  virtualisation.docker.enable = true;

  # System state version
  system.stateVersion = "24.05";
}

