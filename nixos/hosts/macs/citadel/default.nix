{
  vars,
  lib,
  ...
}: {
  imports = [
    ../../../modules/darwin/common.nix
    ../../../modules/darwin/home.nix
    ../../../modules/darwin/homebrew-base.nix
    ../../../modules/darwin/omlx.nix
  ];

  networking.hostName = "citadel";

  # Citadel-specific dock order. Overrides the shared persistent-apps list in
  # modules/darwin/common.nix.
  # NOTE: Finder is NOT listed here — macOS always pins it to the far left
  # automatically. Adding /System/Applications/Finder.app produces a second,
  # broken "?" tile, so it is intentionally omitted.
  system.defaults.dock.persistent-apps = lib.mkForce [
    "/Applications/Firefox Nightly.app"
    "/Applications/Ghostty.app"
    "/Applications/Slack.app"
    "/Applications/Obsidian.app"
    "/Applications/Visual Studio Code.app"
    "/Applications/Thunderbird.app"
    "/Applications/Spotify.app"
    "/Applications/Docker.app"
  ];

  # --- Homebrew (work-machine extras) ---
  # Shared baseline (enable, onActivation, common brews/casks, oMLX agent) comes
  # from modules/darwin/homebrew-base.nix. Only citadel-specific additions here.
  homebrew = {
    taps = [
      "hashicorp/tap" # Terraform
    ];

    brews = [
      # Node via volta (manages node/npm/npx shims in ~/.volta/bin)
      "volta"

      # Cloud / Infra
      "hashicorp/tap/terraform"
      "kubernetes-cli"

      # Python version management
      "pyenv"
      "xz"
    ];

    casks = [
      "firefox@nightly"
      "firefox@developer-edition"
      "magic-wormhole"

      # Communication
      "zoom"
      "google-drive"
      "thunderbird"

      # Dev
      "google-cloud-sdk"

      # Networking
      "mozilla-vpn"
    ];
  };

  # Deploy oMLX with citadel-specific settings (12GB hot cache for M5 Pro 48GB).
  # The stow + jq-merge + restart logic lives in modules/darwin/omlx.nix.
  services.omlxDeploy = {
    enable = true;
    cacheSize = "12GB";
  };

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

    # Citadel is the Mozilla work machine: attribute commits to the Mozilla identity and
    # sign them with the on-host SSH key (added to the GregHilstonMozilla GitHub account),
    # overriding the shared gmail identity + openpgp signing from the tui/git module.
    programs.git = {
      settings.user = {
        name = lib.mkForce "GregHilstonMozilla";
        email = lib.mkForce "ghilston@mozilla.com";
      };
      signing = {
        format = lib.mkForce "ssh";
        key = "/Users/${vars.user.name}/.ssh/id_rsa.pub";
        signByDefault = true; # sign every commit/tag -> "Verified" on GitHub
      };
    };

    # Volta (Node version manager) — citadel only
    home.file.".zshrc.local".text = lib.mkAfter ''

      # ── Volta (Node version manager) ────────────────────────────────
      export VOLTA_HOME="$HOME/.volta"
      export PATH="$VOLTA_HOME/bin:$PATH"
    '';
  };
}
