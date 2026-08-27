{
  inputs,
  vars,
  lib,
  pkgs,
  ...
}: {
  imports = [
    ../../../modules/darwin/common.nix
    ../../../modules/darwin/home.nix
    ../../../modules/darwin/homebrew-base.nix
    ../../../modules/darwin/omlx.nix
    # Launch Handy at login so the Caps-Lock-hold → F18 dictation hotkey works
    # without opening the app by hand.
    ../../../modules/darwin/handy.nix
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

      # File transfer CLI (formula, not a cask)
      "magic-wormhole"
    ];

    casks = [
      "firefox@nightly"
      "firefox@developer-edition"

      # Communication
      "zoom"
      "google-drive"
      "thunderbird"

      # Dev
      "google-cloud-sdk"

      # Docker Desktop is citadel-only ON PURPOSE. It used to live in
      # homebrew-base.nix (every Mac), which put it on dungeon and moria alongside
      # OrbStack — see modules/darwin/homebrew-server.nix. Two Docker runtimes on one
      # host fight over /usr/local/bin/docker, and `onActivation.upgrade = true` means
      # every darwin-rebuild re-installs the loser's symlinks. That is exactly what
      # happened on dungeon on 2026-08-17: a Docker Desktop cask bump repointed
      # /usr/local/bin/docker at Docker.app and silently disabled a launchd watchdog
      # that resolved `docker` through it. citadel has no OrbStack, so it is safe here.
      "docker-desktop"

      # Networking
      "mozilla-vpn"
    ];
  };

  # Deploy oMLX with citadel-specific settings (12GB hot cache for M5 Pro 48GB).
  # The symlink + jq-merge + restart logic lives in modules/darwin/omlx.nix.
  services.omlxDeploy = {
    enable = true;
    cacheSize = "12GB";
  };

  home-manager.users.${vars.user.name} = {
    # 6-bit is the best quality/memory balance for 48GB
    custom.programs.pi.defaultModel = lib.mkForce "Qwen3.6-35B-A3B-6bit";

    # Exclude moonpi (cwd error on this host)
    #
    # NOTE: this mkForce replaces the module default outright, so anything added
    # to `packages` in modules/programs/tui/pi.nix reaches moria, dungeon and
    # rohan but silently skips citadel. It has already drifted — moonpi no
    # longer exists, and the bare "npm:pi-agent-suite" here re-adds all 22 of
    # its extensions, which the module default deliberately narrows to three.
    # Worth converting to a subtractive override; until then, new packages have
    # to be added in both places.
    custom.programs.pi.packages = lib.mkForce [
      "npm:@ff-labs/pi-fff"
      "npm:pi-agent-suite"
      "npm:pi-powerline-footer@0.15.1" # keep in sync with modules/programs/tui/pi.nix
    ];

    # Disable modules not needed on this host
    custom.programs.opencode.enable = lib.mkForce false;

    # Disable mflux activation
    home.activation.install-mflux = lib.mkForce "";

    # runlayer — Mozilla's MCP gateway CLI, PyPI-only (no nixpkgs package).
    # Fronts Slack/Jira/Drive MCP connectors behind mozilla.runlayer.com, so it
    # belongs on the work machine only. `runlayer setup install` then wires the
    # chosen connectors into ~/.claude.json.
    home.activation.install-runlayer = inputs.home-manager.lib.hm.dag.entryAfter ["installPackages"] ''
      ${pkgs.uv}/bin/uv tool install --upgrade runlayer 2>/dev/null || true
    '';

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
