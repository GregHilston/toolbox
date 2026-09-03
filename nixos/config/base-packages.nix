# Shared package lists for the NixOS + nix-darwin system configs and both
# home-manager profiles, so the baseline lives in one place.
#
# This is a plain function (NOT a NixOS/nix-darwin module) because the two
# module systems differ; each caller imports it with its own `pkgs`:
#
#   let basePackages = import ../../config/base-packages.nix pkgs;
#   in { environment.systemPackages = basePackages.systemPackages ++ [...]; }
pkgs: {
  # CLI tools installed system-wide on every host (NixOS and Darwin).
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
    gnumake
    docker-compose

    # Modern CLI tools
    direnv # kept in nix for nix-direnv caching (see tui/direnv)
    btop
    bruno-cli
    yq-go
  ];

  # User (home-manager) packages shared by the NixOS and Darwin profiles.
  # A few tools (git, ripgrep, ncdu) intentionally appear here AND in
  # systemPackages: system-wide for root/services, and in the user profile.
  homePackages = with pkgs; [
    ncdu
    ollama
    ripgrep
    hugo
    go
    duckdb
    opencode
    yt-dlp
    ffmpeg # yt-dlp needs it to merge best-quality video+audio streams
    uv
    # Filters shell output before it reaches Claude Code (`rtk hook claude` in
    # dot/claude/.claude/settings.json) and pi (dot/pi/.pi/agent/extensions/rtk.ts).
    # Both fail open when the binary is missing, which is how NixOS hosts ran
    # without it for months; the Macs get it from Homebrew.
    rtk
    # Node runtime for npm-installed CLIs. The Macs already get node from
    # Homebrew (and /opt/homebrew/bin sorts ahead of the nix profiles on PATH,
    # so this does not displace it); NixOS hosts had none, which broke
    # ccstatusline — see modules/programs/tui/claude.nix.
    nodejs_22
    git
    (python3.withPackages (ps:
      with ps; [
        youtube-transcript-api
      ]))
  ];
}
