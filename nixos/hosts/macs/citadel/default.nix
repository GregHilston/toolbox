{
  vars,
  pkgs,
  lib,
  ...
}: {
  imports = [
    ../../../modules/darwin/common.nix
    ../../../modules/darwin/home.nix
    ../../../modules/darwin/omlx.nix
  ];

  networking.hostName = "citadel";

  # --- Homebrew ---
  homebrew = {
    enable = true;

    onActivation = {
      autoUpdate = true;
      cleanup = "none"; # don't touch apps not declared here
      upgrade = true;
    };

    taps = [
      "nikitabobko/tap" # AeroSpace
      "hashicorp/tap" # Terraform
      {
        name = "jundot/omlx";
        clone_target = "https://github.com/jundot/omlx";
      }
    ];

    brews = [
      "stow"
      "tmux"
      "just"
      "pandoc"
      "gh"

      # Node via volta (manages node/npm/npx shims in ~/.volta/bin)
      "volta"

      # Cloud / Infra
      "hashicorp/tap/terraform"
      "kubernetes-cli"

      # Python version management
      "pyenv"
      "xz"

      # AI / LLM
      "jundot/omlx/omlx"
      "pi-coding-agent"
    ];

    casks = [
      # Core
      "ghostty"
      "firefox"
      "firefox@nightly"
      "firefox@developer-edition"
      "visual-studio-code"
      "1password"

      # Communication
      "slack"
      "zoom"
      "google-drive"
      "thunderbird"

      # Media
      "spotify"
      "vlc"

      # Dev
      "bruno"
      "db-browser-for-sqlite"
      "google-cloud-sdk"
      "ngrok"
      "docker-desktop"
      "dbeaver-community"

      # Drivers
      "displaylink"

      # Productivity
      "obsidian"
      "raycast"
      "stats"
      "jordanbaird-ice"
      "aerospace"

      # Productivity
      "mozilla-vpn"
    ];
  };

  # oMLX launchd agent — starts inference server at login
  launchd.user.agents.omlx = {
    command = "/opt/homebrew/bin/omlx serve";
    serviceConfig = {
      RunAtLoad = true;
      KeepAlive = true;
      StandardOutPath = "/Users/${vars.user.name}/Library/Logs/omlx.log";
      StandardErrorPath = "/Users/${vars.user.name}/Library/Logs/omlx.log";
    };
  };

  # Deploy oMLX with citadel-specific settings (12GB hot cache for M5 Pro 48GB)
  system.activationScripts.postActivation.text = lib.mkBefore ''
    export PATH="${pkgs.stow}/bin:${pkgs.jq}/bin:$PATH"
    TOOLBOX="/Users/${vars.user.name}/Git/toolbox/dot"

    cd "$TOOLBOX"
    stow -R --no-folding omlx

    # Merge base settings.json + citadel overlay → ~/.omlx/settings.json
    OMLX_SETTINGS="/Users/${vars.user.name}/.omlx/settings.json"
    jq -s '.[0] * .[1]' \
      "$TOOLBOX/omlx/.omlx/settings.json" \
      "$TOOLBOX/omlx-citadel/.omlx/settings.json" \
      > "$OMLX_SETTINGS.tmp"
    mv -f "$OMLX_SETTINGS.tmp" "$OMLX_SETTINGS"

    launchctl kickstart -k "gui/$(id -u ${vars.user.name})/org.nixos.omlx" 2>/dev/null || true

    echo "✓ oMLX configured for citadel (hot_cache_max_size=12GB)"
  '';

  home-manager.users.${vars.user.name} = {
    # 6-bit is the best quality/memory balance for 48GB
    custom.programs.pi.defaultModel = lib.mkForce "Qwen3.6-35B-A3B-6bit";

    # Exclude moonpi (cwd error on this host)
    custom.programs.pi.packages = lib.mkForce [
      "npm:@ff-labs/pi-fff"
      "npm:pi-agent-suite"
    ];

    # Disable modules not needed on this host
    custom.programs.opencode.enable = lib.mkForce false;

    # Disable mflux activation
    home.activation.install-mflux = lib.mkForce "";

    # Volta (Node version manager) — citadel only
    home.file.".zshrc.local".text = lib.mkAfter ''

      # ── Volta (Node version manager) ────────────────────────────────
      export VOLTA_HOME="$HOME/.volta"
      export PATH="$VOLTA_HOME/bin:$PATH"
    '';
  };
}
