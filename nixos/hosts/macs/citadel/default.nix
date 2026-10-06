{
  config,
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
    # FluidVoice: Caps Lock dictates; Shift/Option pick Command/Write Mode.
    ../../../modules/darwin/fluidvoice.nix
    # Vorssaint — the menu-bar utility suite. Per-host (citadel, moria) rather
    # than from common.nix: headless dungeon has no one sitting at a menu bar,
    # and almost every feature is an interactive one. The feature set it comes
    # up with is the module's `features` default.
    ../../../modules/darwin/vorssaint.nix
    ../../../modules/darwin/hermes-desktop.nix
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
      "mozilla/mozcloud" # mzcld
    ];

    brews = [
      # Node via volta (manages node/npm/npx shims in ~/.volta/bin)
      "volta"

      # Cloud / Infra
      "hashicorp/tap/terraform"
      "kubernetes-cli"
      # Yardstick (Grafana): IAP proxy and CLI
      "mozilla/mozcloud/mzcld"
      "gcx"

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
      "gcloud-cli"

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

  # Rare local use: on-demand load, idle unload.
  # Balanced tier refused the 20 GB model (18 GB reclaimable).
  # The symlink + jq-merge + restart logic lives in modules/darwin/omlx.nix.
  services.omlxDeploy = {
    enable = true;
    cacheSize = "2GB";
    memoryCeilingGB = 28;
    idleTimeoutSeconds = 1800;
  };

  # Yardstick (Grafana) IAP proxy on :3000.
  # grafana MCP and gcx both point here. Needs `gcloud auth login`; mzcld
  # shells out to gcloud, so its brew bin must be on PATH.
  # SRE doc: https://mozilla-hub.atlassian.net/wiki/spaces/SRE/pages/2641985695
  launchd.user.agents.yardstick-proxy = {
    command = "/opt/homebrew/bin/mzcld iap --host yardstick.mozilla.org --proxy --port 3000";
    serviceConfig = {
      RunAtLoad = true;
      KeepAlive = true;
      # Back off when gcloud auth has expired
      ThrottleInterval = 60;
      EnvironmentVariables.PATH = "/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin";
      StandardOutPath = "/Users/${vars.user.name}/Library/Logs/yardstick-proxy.log";
      StandardErrorPath = "/Users/${vars.user.name}/Library/Logs/yardstick-proxy.log";
    };
  };

  # Vorssaint — menu-bar utility suite (imported above). Seeds its Features hub
  # once on a Mac that has never run it; after that the hub owns the choice.
  # The feature list, and what it deliberately leaves out to stay clear of
  # Karabiner and AeroSpace, is in modules/darwin/vorssaint.nix.
  services.vorssaint.enable = true;

  services.fluidvoice.enable = true;

  services.hermesDesktop.enable = true;

  home-manager.users.${vars.user.name} = {
    # Personal metered spend, never from work.
    custom.programs.pi.deepseek = false;
    # Work machine: its own oMLX, never the home lab's gateway.
    custom.programs.pi.gateway = false;
    custom.programs.pi.defaultModel = "${config.services.omlxDeploy.lightModel.dir}:lab";

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
      "npm:pi-powerline-footer"
      # Runlayer MCPs, work machine only. Servers below.
      "npm:pi-mcp-adapter"
    ];

    # pi-mcp-adapter's config: the Runlayer servers Claude Code has in
    # ~/.claude.json, over the same HTTP proxy URLs. pi OAuths to Runlayer
    # once per server; Runlayer holds the upstream tokens. Not stdio
    # `runlayer run`: that does upstream OAuth locally, which Runlayer has
    # misconfigured for Slack and Figma (see `runlayer doctor <uuid>`).
    # Proxy mode (directTools = false) costs one ~800-token `mcp` tool
    # regardless of server count; see dot/pi/CLAUDE.md.
    # allowInstall is off because this file is a read-only /nix/store symlink.
    home.file.".pi/agent/mcp-adapter.json".text = let
      runlayer = uuid: {
        url = "https://mozilla.runlayer.com/api/v1/proxy/${uuid}/mcp";
        auth = "oauth";
      };
    in
      builtins.toJSON {
        settings = {
          directTools = false;
          allowInstall = false;
        };
        mcpServers = {
          slack = runlayer "12c6b691-9efb-4630-ba42-35aaee7e53df";
          github-mozilla-orgs = runlayer "a256a9b0-9d38-44ae-b8ae-6bf873ff8ac8";
          figma = runlayer "c8f06e5a-41a2-4994-b08d-645c3c6e578a";
          gmail = runlayer "1001bd70-ca7d-49a2-b297-cb8a343cf2dc";
          google-docs = runlayer "7620cea5-f374-4c00-9427-7cefa55d364f";
          google-drive = runlayer "5abc0569-9253-4488-8e95-2fc7bba3a2fd";
          google-sheets = runlayer "2cf7b2fc-b49b-49f7-923c-06b591f43b8e";
          google-slides = runlayer "a87df1eb-4309-46f7-9ab4-a6acc1d242cb";
          # Jira and Confluence. Atlassian's own endpoint, not Runlayer.
          atlassian = {
            url = "https://mcp.atlassian.com/v1/mcp";
            auth = "oauth";
          };
        };
      };

    # Citadel-specific packages. gitleaks scans work repos for secrets.
    home.packages = with pkgs; [
      gitleaks
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

    # quick — publishes a static dir to <name>.quick.mozilla.cloud. A Go binary
    # in the internal mozilla/quick repo, so no nixpkgs package, no tap, and
    # `fetchurl` cannot reach it: every download path is behind Mozilla SSO.
    # Work machine only, so it lives here rather than in a shared module.
    #
    # Fetched with gh, not the `gcloud storage cp gs://moz-fx-quick-prod-cli/...`
    # the landing page documents — gcloud's tokens expire and reauth wants a
    # browser, which activation cannot give it (already seen: `Reauthentication
    # failed. cannot prompt during non-interactive execution`). gh's keyring
    # token does not expire. /opt/homebrew/bin/gh, not ${pkgs.gh}: it is the
    # binary the keychain item is scoped to, and activation's PATH is stripped.
    #
    # One-shot, because `quick update` self-updates from the prod bucket. To
    # reinstall, delete ~/.local/bin/quick and re-run `just dr citadel`.
    #
    # The CLI itself still needs `gcloud auth login` (gcloud-cli is in the
    # casks above) — it shells out to gcloud for every command.
    home.activation.install-quick = inputs.home-manager.lib.hm.dag.entryAfter ["installPackages"] ''
      if [ ! -x "$HOME/.local/bin/quick" ]; then
        mkdir -p "$HOME/.local/bin"
        # Download beside the target, then rename: a half-written binary on PATH
        # is worse than an absent one.
        if /opt/homebrew/bin/gh release download --repo mozilla/quick \
             --pattern quick-darwin-arm64 \
             --output "$HOME/.local/bin/.quick.download" --clobber 2>/dev/null; then
          chmod +x "$HOME/.local/bin/.quick.download"
          mv "$HOME/.local/bin/.quick.download" "$HOME/.local/bin/quick"
          echo "✓ quick installed to ~/.local/bin/quick"
        else
          rm -f "$HOME/.local/bin/.quick.download"
          echo "WARNING: could not download quick from mozilla/quick." >&2
          echo "  Needs 'gh auth login' on the Mozilla account (the repo is internal)." >&2
        fi
      fi
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
