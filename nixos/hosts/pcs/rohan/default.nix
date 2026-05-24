# Writerdeck — a dedicated distraction-free writing device.
#
# No browser, no desktop environment, no development tools. Just a terminal
# with neovim, tmux, and zsh. Boots to a TTY login prompt.
#
# Inspired by:
#   https://veronicaexplains.net/my-first-writerdeck/
#   https://writerdeckos.com/
#
# Hardware: ThinkPad X201 Tablet (x86_64, built-in Wacom digitizer)
#
# File transfer: SSH/scp/rsync (no syncthing, no GUI file manager)
# Networking: NetworkManager with nm-tui for wifi
{
  inputs,
  lib,
  pkgs,
  vars,
  ...
}: {
  imports = [
    ./hardware-configuration.nix
    inputs.home-manager.nixosModules.home-manager
    ../../../modules/stylix
  ];

  networking = {
    hostName = "rohan";
    networkmanager.enable = true;
  };

  # Boot — GRUB for legacy BIOS (X201 era hardware)
  boot.loader.grub = {
    enable = true;
    device = "/dev/sda";
  };

  nix.settings.experimental-features = ["nix-command" "flakes"];

  nixpkgs.config.allowUnfree = true;

  time.timeZone = vars.system.timeZone;

  i18n = {
    defaultLocale = vars.system.locale;
    extraLocaleSettings = {
      LC_ADDRESS = vars.system.locale;
      LC_IDENTIFICATION = vars.system.locale;
      LC_MEASUREMENT = vars.system.locale;
      LC_MONETARY = vars.system.locale;
      LC_NAME = vars.system.locale;
      LC_NUMERIC = vars.system.locale;
      LC_PAPER = vars.system.locale;
      LC_TELEPHONE = vars.system.locale;
      LC_TIME = vars.system.locale;
    };
  };

  # SSH for file transfer (scp/rsync)
  services.openssh.enable = true;

  # No desktop environment — writerdeck boots to TTY
  # No xserver, no display manager, no pipewire, no Docker

  # 1Password CLI for secret access (no GUI)
  programs._1password.enable = true;

  # Battery optimization for laptop use
  powerManagement.powertop.enable = true;

  users.users.${vars.user.name} = {
    initialPassword = "password";
    isNormalUser = true;
    description = vars.user.fullName;
    extraGroups = ["networkmanager" "wheel"];
    ignoreShellProgramCheck = true;
    shell = pkgs.${vars.user.packages.shell};
    openssh.authorizedKeys.keys = [
      "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCmEoG6aAA559ZIVc4citslV5TxVTb3tbheaSTB/+bo1uOi/IDVS/yEgDqObY2KvP7uqeNqn10diVoe0Pg4yLiFTuNriFA6aPmhs00DjazttGj8WyFDOJnBIg1NL9BlewvkxlSXa/LsWfN8JanZ1Cwknff8jxxbm+s1CxV8+XWWK4MHsfHixfD69UP437cJ9QuomKFrWZ4A+s4SUHfKVknFn0xDgclay3/h6cAdc9+rlYe73UY6AzeqgKlOxL1S1NNn2TIyhmBQm32xhsW++LLpG/4jv1+pgRHeghmJYPk1+ZeGkGRi/oRSibMActa960WBccHOMxCTVDhF/Rkyw4RoMCU/gU3zFY8Nm92xM34+SU23Sf1xdP6Gs2/raQIf49bVOkGNZXtmHBh+dvnTBxmgXcyHHoJGLPYy/Ct/IYYoeRn6lRxiBSidu0kk9hwL0JqF75a7wDlHXN4hWLXvma4RKrIgGt8pJGsjjIa1bWSKKUowuLgm56PCDC0Dxa95fBE= moria (macbook pro)"
    ];
  };

  # Minimal system packages — only what's needed for writing and file transfer
  environment = {
    systemPackages = with pkgs; [
      bat
      curl
      fastfetch
      git
      htop
      jq
      just
      neovim
      rsync
      stow
      tmux
      tree
      wget
      zsh
    ];
    sessionVariables = {
      EDITOR = "nvim";
    };
  };

  # Home-manager — cherry-pick only writing-relevant TUI modules
  home-manager = {
    useUserPackages = true;
    backupFileExtension = "backup";
    extraSpecialArgs = {
      inherit inputs vars;
      outputs = {};
    };
    users.${vars.user.name} = {
      imports = [
        ../../../modules/programs/tui/claude.nix
        ../../../modules/programs/tui/direnv
        ../../../modules/programs/tui/eza
        ../../../modules/programs/tui/fzf
        ../../../modules/programs/tui/git
        ../../../modules/programs/tui/neovim
        ../../../modules/programs/tui/pi.nix
        ../../../modules/programs/tui/tmux
        ../../../modules/programs/tui/zoxide
        ../../../modules/programs/tui/zsh
      ];

      nixpkgs.config.allowUnfree = true;

      home = {
        username = vars.user.name;
        homeDirectory = "/home/${vars.user.name}";
        packages = with pkgs; [
          aspell
          aspellDicts.en
          claude-code
          glow
          pandoc
          pi-coding-agent
          ripgrep
          wordgrinder
        ];
      };

      # Pi mono — point to dungeon's oMLX server, not local inference
      custom.programs.pi = {
        enable = true;
        defaultModel = "Qwen3.6-27B-8bit";
      };

      # Override models.json to use dungeon's LAN IP instead of localhost.
      # Other hosts use stow + 1Password template; rohan declares it inline
      # to avoid running models locally on this low-power writerdeck.
      home.file.".pi/agent/models.json".text = builtins.toJSON {
        providers = {
          omlx = {
            baseUrl = "http://${vars.networking.hosts.dungeon.lan}:8000/v1";
            api = "openai-completions";
            apiKey = "no-key-needed";
            compat = {
              supportsDeveloperRole = false;
              supportsReasoningEffort = false;
            };
            models = [
              {
                id = "Qwen3.6-27B-8bit";
                name = "Qwen 3.6 27B 8-bit (thinking, 262k ctx, balanced)";
                contextWindow = 262144;
                maxTokens = 81920;
                input = ["text" "image"];
                cost = {
                  input = 0;
                  output = 0;
                  cacheRead = 0;
                  cacheWrite = 0;
                };
              }
              {
                id = "Qwen3.6-27B-4bit";
                name = "Qwen 3.6 27B 4-bit (thinking, 262k ctx, fast)";
                contextWindow = 262144;
                maxTokens = 81920;
                input = ["text" "image"];
                cost = {
                  input = 0;
                  output = 0;
                  cacheRead = 0;
                  cacheWrite = 0;
                };
              }
            ];
          };
        };
      };

      programs.home-manager.enable = true;
      home.stateVersion = "24.05";
    };
  };

  system.stateVersion = "24.05";
}
