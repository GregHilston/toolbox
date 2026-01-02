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

  users.users.${vars.user.name} = {
    initialPassword = "password";
    isNormalUser = true;
    description = "${vars.user.fullName}";
    extraGroups = ["networkmanager" "wheel" "input" "docker"];
    ignoreShellProgramCheck = true;
    shell = pkgs.${vars.user.packages.shell};
    openssh.authorizedKeys.keys = [
      "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCmEoG6aAA559ZIVc4citslV5TxVTb3tbheaSTB/+bo1uOi/IDVS/yEgDqObY2KvP7uqeNqn10diVoe0Pg4yLiFTuNriFA6aPmhs00DjazttGj8WyFDOJnBIg1NL9BlewvkxlSXa/LsWfN8JanZ1Cwknff8jxxbm+s1CxV8+XWWK4MHsfHixfD69UP437cJ9QuomKFrWZ4A+s4SUHfKVknFn0xDgclay3/h6cAdc9+rlYe73UY6AzeqgKlOxL1S1NNn2TIyhmBQm32xhsW++LLpG/4jv1+pgRHeghmJYPk1+ZeGkGRi/oRSibMActa960WBccHOMxCTVDhF/Rkyw4RoMCU/gU3zFY8Nm92xM34+SU23Sf1xdP6Gs2/raQIf49bVOkGNZXtmHBh+dvnTBxmgXcyHHoJGLPYy/Ct/IYYoeRn6lRxiBSidu0kk9hwL0JqF75a7wDlHXN4hWLXvma4RKrIgGt8pJGsjjIa1bWSKKUowuLgm56PCDC0Dxa95fBE= moria (macbook pro)"
    ];
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
      docker-compose

      # Modern CLI tools
      btop # Modern replacement for htop with graphs and better UI
      bruno-cli # CLI for Bruno API client
      gh # GitHub CLI for PRs, issues, and repo management
      yq-go # YAML processor (jq for YAML files)
    ];

    sessionVariables = {
      EDITOR = "nvim";
    };
  };

  system.stateVersion = "24.05";
}
