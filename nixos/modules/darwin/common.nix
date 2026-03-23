{
  inputs,
  vars,
  pkgs,
  ...
}: {
  # Nix settings
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

  # Primary user (required for system.defaults, homebrew, etc.)
  system.primaryUser = vars.user.name;

  # User setup
  users.users.${vars.user.name} = {
    home = "/Users/${vars.user.name}";
    shell = pkgs.${vars.user.packages.shell};
  };

  # System packages (CLI tools available system-wide)
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
      tree
      ncdu
      just
      gcc
      lazygit
      ripgrep
      fd
      python3
      pandoc
      gnumake
      docker-compose

      # Modern CLI tools
      btop
      bruno-cli
      gh
      yq-go
    ];

    variables = {
      EDITOR = "nvim";
    };
  };

  # macOS system preferences (declarative)
  system.defaults = {
    dock = {
      autohide = true;
      show-recents = false;
      mru-spaces = false;
      minimize-to-application = true;
    };

    finder = {
      AppleShowAllExtensions = true;
      FXPreferredViewStyle = "Nlsv"; # List view
      ShowPathbar = true;
      ShowStatusBar = true;
      _FXShowPosixPathInTitle = true;
    };

    NSGlobalDomain = {
      AppleShowAllExtensions = true;
      AppleInterfaceStyle = "Dark";
      InitialKeyRepeat = 15;
      KeyRepeat = 2;
      NSAutomaticCapitalizationEnabled = false;
      NSAutomaticSpellingCorrectionEnabled = false;
    };

    trackpad = {
      Clicking = true;
      TrackpadRightClick = true;
      TrackpadThreeFingerDrag = true;
    };
  };

  # Touch ID for sudo
  security.pam.services.sudo_local.touchIdAuth = true;

  # Timezone
  time.timeZone = vars.system.timeZone;

  # nix-darwin state version
  system.stateVersion = 6;
}
