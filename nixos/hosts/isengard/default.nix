{ inputs, outputs, lib, config, pkgs, vars, ... }:

{
  imports = [
    ./hardware-configuration.nix
    inputs.home-manager.nixosModules.home-manager
  ];

  system.autoUpgrade = {
    enable = true;
    allowReboot = true;
  };

  home-manager = {
    extraSpecialArgs = {
      inherit inputs outputs vars;
    };
    users.${vars.user} = import ../../modules/home;
  };

  nix.settings.experimental-features = [ "nix-command" "flakes" ];

  nixpkgs.config.allowUnfree = true;

  boot = {
    loader.grub.enable = true;
    loader.grub.device = "/dev/sda";
    loader.grub.useOSProber = true;
  }; 

  networking = {
    networkmanager.enable = true;
    hostName = "nixos"; # TODO replace with variable for hostname
  };

  time.timeZone = "America/New_York";

  i18n = {
    defaultLocale = "en_US.UTF-8";
    extraLocaleSettings = {
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
  };

  virtualisation.docker.enable = true;

  services = {
    # Enable the X11 windowing system
    xserver.enable = true;

    # Enable the KDE Plasma Desktop Environment
    displayManager.sddm.enable = true;
    desktopManager.plasma6.enable = true;

    # Configure keymap in X11
    xserver.xkb = {
      layout = "us";
      variant = "";
    };

    # Enable sound with pipewire
    pipewire = {
      enable = true;
      alsa.enable = true;
      alsa.support32Bit = true;
      pulse.enable = true;
    };

    # OpenSSH service
    openssh.enable = true;
    openssh.settings.X11Forwarding = true;
  };

  security = {
    rtkit.enable = true;
  };

  # auto-tune on start
  powerManagement.powertop.enable = true;

  # Define a user account. Don't forget to set a password with ‘passwd’.
  users.users.${vars.user} = {
    initialPassword = "password";
    isNormalUser = true;
    description = "${vars.name}";
    extraGroups = [ "networkmanager" "wheel" "input" "docker" ];
    ignoreShellProgramCheck = true;
    shell = pkgs.${vars.shell};
  };

  environment = {
    # Install useful system-wide packages
    systemPackages = with pkgs; [
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
      gcc # Needed for LazyVim's usage of nvim-treesitter
      nerdfonts # Needed for LazyVim's display of some icons
      lazygit # Needed for LazyVim
      ripgrep # Needed for LazyVim
      fd # Needed for LazyVim
      python3
    ];

    # Set session variables
    sessionVariables = {
      EDITOR = "nvim";
    };
  };

  programs = {
    firefox.enable = true;
  };

  fonts.packages = with pkgs; [
    nerdfonts
  ];

  # https://nixos.wiki/wiki/FAQ/When_do_I_update_stateVersion
  system.stateVersion = "24.05";
}
