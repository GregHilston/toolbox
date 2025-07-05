{
  inputs,
  outputs,
  lib,
  config,
  pkgs,
  vars,
  ...
} @ args:
# Optional: give a name to the whole argument set
{
  imports = [
    inputs.home-manager.nixosModules.home-manager
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

  nix.settings.experimental-features = ["nix-command" "flakes"];

  nixpkgs = {
    overlays = [
      inputs.nur.overlays.default
      inputs.nix-vscode-extensions.overlays.default
    ];
    config = {
      allowUnfree = true;
    };
  };

  networking.networkmanager.enable = true;

  time.timeZone = vars.system.timeZone;

  i18n = {
    defaultLocale = vars.system.locale;
    extraLocaleSettings = {
      LC_ADDRESS = vars.system.locale;
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

  programs.nix-ld.enable = true;

  virtualisation.docker.enable = true;

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

  users.users.${vars.user.name} = {
    initialPassword = "password";
    isNormalUser = true;
    description = "${vars.user.fullName}";
    extraGroups = ["networkmanager" "wheel" "input" "docker"];
    ignoreShellProgramCheck = true;
    shell = pkgs.${vars.user.packages.shell};
  };

  environment = {
    systemPackages = with pkgs; [
      bat
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
      gcc
      lazygit
      ripgrep
      fd
      python3
      pandoc
      xclip
      gnumake
    ];

    sessionVariables = {
      EDITOR = "nvim";
    };
  };

  system.stateVersion = "24.05";
}
