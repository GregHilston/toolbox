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
    ../../../modules/common/core.nix
    ../../../modules/stylix
  ];

  # nix settings, networkmanager, timeZone, locale, and the base user come
  # from ../../../modules/common/core.nix (shared with modules/common).
  networking.hostName = "rohan";

  # Boot — GRUB for legacy BIOS (X201 era hardware)
  boot.loader.grub = {
    enable = true;
    device = "/dev/sda";
  };

  # nixpkgs overlays + allowUnfree come from the shared nixpkgsModule in
  # flake-modules/hosts.nix (applied to every host via mkNixos).

  # USB wifi dongle (Realtek RTL8188EUS) needs firmware blobs
  hardware.enableRedistributableFirmware = true;

  # SSH for file transfer (scp/rsync)
  services.openssh.enable = true;

  # Auto-login to TTY — no username/password prompt on boot
  services.getty.autologinUser = vars.user.name;

  # No desktop environment — writerdeck boots to TTY
  # No xserver, no display manager, no pipewire, no Docker

  # Register zsh as a system shell and suppress zsh-newuser-install wizard
  programs.zsh.enable = true;

  # 1Password CLI for secret access (no GUI)
  programs._1password.enable = true;

  # Battery optimization for laptop use
  powerManagement.powertop.enable = true;

  # Backlight control — without a DE, Fn+brightness keys need acpid with
  # explicit handlers. Manual fallback: brightnessctl set +10% / 10%-
  hardware.acpilight.enable = true;
  services.acpid = {
    enable = true;
    handlers = {
      brightness-up = {
        event = "video/brightnessup";
        action = "${pkgs.brightnessctl}/bin/brightnessctl set +10%";
      };
      brightness-down = {
        event = "video/brightnessdown";
        action = "${pkgs.brightnessctl}/bin/brightnessctl set 10%-";
      };
    };
  };

  # kmscon — replaces the default Linux VT with a userspace console that
  # supports TrueType fonts (Nerd Font glyphs for Powerlevel10k) and 256 colors.
  # See: https://veronicaexplains.net/my-first-writerdeck/
  #
  # The kmscon module dropped services.kmscon.{fonts,extraConfig}. Stylix already
  # themes the console font (its JetBrainsMono Nerd Font monospace + fontconfig),
  # so we only bump the console font size for the X201's small display and pass
  # the term options via the new freeform services.kmscon.config / extraOptions.
  services.kmscon = {
    enable = true;
    # mkForce overrides the size stylix derives from its terminal font size.
    config.font-size = lib.mkForce 14;
    extraOptions = "--term xterm-256color --no-mouse";
  };

  # The primary user (with the moria ssh key, groups networkmanager + wheel)
  # comes from ../../../modules/common/core.nix.

  # Minimal system packages — only what's needed for writing and file transfer
  environment = {
    systemPackages = with pkgs; [
      bat
      brightnessctl
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

  # Home-manager — cherry-pick only writing-relevant TUI modules.
  # useGlobalPkgs/useUserPackages/backupFileExtension come from the shared
  # mkHomeManagerModule in flake-modules/hosts.nix.
  home-manager = {
    extraSpecialArgs = {
      inherit inputs vars;
      outputs = {};
    };
    users.${vars.user.name} = {
      imports = [
        ../../../modules/programs/tui/atuin
        ../../../modules/programs/tui/claude.nix
        ../../../modules/programs/tui/direnv
        ../../../modules/programs/tui/eza
        ../../../modules/programs/tui/fzf
        ../../../modules/programs/tui/git
        ../../../modules/programs/tui/neovim
        ../../../modules/programs/tui/pi.nix
        ../../../modules/programs/tui/tmux
        ../../../modules/programs/tui/ssh.nix
        ../../../modules/programs/tui/yazi.nix
        ../../../modules/programs/tui/zoxide
        ../../../modules/programs/tui/zsh
      ];

      # allowUnfree comes from the system nixpkgs via useGlobalPkgs
      # (set in the shared mkHomeManagerModule in flake-modules/hosts.nix).

      home = {
        username = vars.user.name;
        homeDirectory = "/home/${vars.user.name}";
        packages = with pkgs; [
          aspell
          aspellDicts.en
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

      # Writerdeck MOTD + auto-tmux — append to .zshrc.local
      # which is sourced by the shared .zshrc at the end
      home.file.".zshrc.local".text = lib.mkAfter ''

        # ── Writerdeck MOTD (shows in every interactive shell) ───────────
        if [[ -o interactive ]]; then
          echo ""
          echo "  Welcome to rohan — your writerdeck."
          echo "  Notes: ~/notes/"
          echo ""
          echo "  Quick reference:"
          echo "    nvim <file>              edit with neovim"
          echo "    wordgrinder              TUI word processor"
          echo "    glow <file.md>           preview markdown"
          echo "    aspell check <file>      spell check"
          echo "    pandoc <in> -o <out>     convert formats"
          echo ""
          echo "    nmcli device wifi list   scan wifi"
          echo "    nmcli device wifi connect \"SSID\" password \"pass\""
          echo ""
        fi

        # ── Auto-start tmux on login (not inside tmux) ──────────────────
        if [[ -o interactive ]] && [[ -z "$TMUX" ]] && command -v tmux &>/dev/null; then
          exec tmux new-session
        fi
      '';

      programs.home-manager.enable = true;
      home.stateVersion = "24.05";
    };
  };

  system.stateVersion = "24.05";
}
