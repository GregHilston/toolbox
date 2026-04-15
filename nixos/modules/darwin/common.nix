{
  inputs,
  vars,
  pkgs,
  ...
}: {
  # Let Determinate manage the Nix daemon; disable nix-darwin's nix management
  nix.enable = false;

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
      gcc
      lazygit
      ripgrep
      fd
      python3
      gnumake
      docker-compose

      # Modern CLI tools
      direnv # kept in nix for nix-direnv caching (see tui/direnv)
      btop
      bruno-cli
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
      persistent-apps = [
        "/System/Applications/Finder.app"
        "/Applications/Firefox.app"
        "/Applications/Ghostty.app"
        "/Applications/Slack.app"
        "/Applications/Obsidian.app"
        "/Applications/Visual Studio Code.app"
        "/Applications/Bruno.app"
      ];
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
      "com.apple.swipescrolldirection" = false; # Disable natural scrolling
    };

    trackpad = {
      Clicking = true;
      TrackpadRightClick = true;
      TrackpadThreeFingerDrag = true;
    };

    screencapture = {
      location = "/Users/${vars.user.name}/Pictures/screenshots";
    };
  };

  # Power management - display sleep timeout (in minutes)
  power.sleep.display = 5;

  # Touch ID for sudo
  security.pam.services.sudo_local.touchIdAuth = true;

  # Timezone
  time.timeZone = vars.system.timeZone;

  # Ensure screenshot directory exists
  system.activationScripts.preActivation.text = ''
    mkdir -p /Users/${vars.user.name}/Pictures/screenshots
  '';

  # Post-activation reminder for manual setup steps
  system.activationScripts.postActivation.text = ''
    echo ""
    echo "NOTE: There are manual steps that may need to be applied for an initial setup."
    echo "      See nixos/modules/darwin/README.md"
    echo ""

    # Reduce spacing between menu bar icons to fit more items
    # https://news.ycombinator.com/item?id=47618946
    defaults -currentHost write -globalDomain NSStatusItemSpacing -int 2
    defaults -currentHost write -globalDomain NSStatusItemSelectionPadding -int 2
  '';

  # Enable zsh system-wide so nix-darwin registers it as a valid shell.
  # The actual shell config is stow-managed (dot/zsh/.zshrc).
  programs.zsh.enable = true;

  # nix-darwin state version
  system.stateVersion = 6;
}
