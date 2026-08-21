{
  config,
  lib,
  pkgs,
  vars,
  ...
}: let
  cfg = config.custom.programs.pi;

  # A packages entry is either a source string or pi's filtering object form.
  # `pi install` only ever takes the source, so unwrap it for the activation
  # script while settings.json keeps the full entry.
  packageSource = pkg:
    if builtins.isString pkg
    then pkg
    else pkg.source;

  # One oMLX model entry. Everything except id/name has a sane default because
  # every model we serve shares the same shape, and `cost` is not an option at
  # all — local inference is free, so it is always zero.
  modelType = lib.types.submodule {
    options = {
      id = lib.mkOption {
        type = lib.types.str;
        description = "Model id exactly as oMLX serves it.";
      };
      name = lib.mkOption {
        type = lib.types.str;
        description = "Human-readable label shown in pi's model picker.";
      };
      contextWindow = lib.mkOption {
        type = lib.types.int;
        default = 262144;
        description = "Context window in tokens.";
      };
      maxTokens = lib.mkOption {
        type = lib.types.int;
        default = 81920;
        description = "Maximum tokens the model may generate in one response.";
      };
      input = lib.mkOption {
        type = lib.types.listOf (lib.types.enum ["text" "image"]);
        default = ["text" "image"];
        description = "Input modalities the model accepts.";
      };
    };
  };
in {
  options.custom.programs.pi = {
    enable = lib.mkEnableOption "pi (pi-mono coding agent)";

    defaultModel = lib.mkOption {
      type = lib.types.str;
      default = "Qwen3.6-35B-A3B-8bit";
      description = "Default model to use";
    };

    # models.json normally comes from stow + `just secrets` (it holds the oMLX
    # api key, so it is templated from 1Password). Hosts that talk to *another*
    # machine's oMLX server have no secret to inject and can declare the file
    # here instead — set omlxBaseUrl and the module generates models.json.
    omlxBaseUrl = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      example = "http://192.168.1.238:8000/v1";
      description = ''
        When non-null, generate ~/.pi/agent/models.json pointing pi's `omlx`
        provider at this base URL, listing `models`. When null (the default),
        models.json is left to stow + `just secrets`.
      '';
    };

    models = lib.mkOption {
      type = lib.types.listOf modelType;
      default = [];
      description = "Models to expose under the generated `omlx` provider. Only used when omlxBaseUrl is set.";
    };

    # Where the web-search extension sends queries. SearXNG runs as a container
    # on dungeon (home-lab), so every other host reaches it over the tailnet.
    # dungeon itself overrides this to localhost.
    searxngBaseUrl = lib.mkOption {
      type = lib.types.str;
      default = "http://${vars.networking.hosts.dungeon.tailscale}:8214";
      example = "http://localhost:8214";
      description = ''
        Base URL of the SearXNG instance pi's `web_search` tool queries. Written
        to ~/.pi/agent/searxng.json, which dot/pi/.pi/agent/extensions/web-search.ts
        reads. Deliberately not a literal in the extension: only nix knows each
        host's answer, and hardcoding one silently breaks the others.
      '';
    };

    # Packages installed via `pi install`. Pi resolves these at runtime.
    # Git-based packages are cloned to ~/.pi/agent/git/; npm packages go to
    # the global node_modules. Local extensions live in ~/.pi/agent/extensions/
    # managed by stow from dot/pi/.
    #
    # Entries are either a plain source string, or pi's object form for
    # filtering what a package loads (docs/packages.md -> "Package Filtering").
    # The object form matters here: on a local model every tool schema and every
    # line of injected system prompt is re-sent on EVERY request, so a package
    # that ships 22 extensions is not free just because we only wanted three.
    packages = lib.mkOption {
      type = lib.types.listOf (lib.types.either lib.types.str (lib.types.attrsOf lib.types.anything));
      default = [
        # Rust-powered frecency-ranked, fuzzy, git-aware file search
        # https://github.com/dmtrKovalenko/fff
        "npm:@ff-labs/pi-fff"

        # Context management, but it ships 22 extensions and we want three.
        # Excluded, and why:
        #   codex-*        OpenAI Codex quota/verbosity features. This host is
        #                  strictly local oMLX, so they are dead weight.
        #   mcp-wrapper    superseded by pi-mcp-adapter below; loading both
        #                  gives two MCP layers.
        # https://github.com/n-r-w/pi-agent-suite
        {
          source = "npm:pi-agent-suite";
          extensions = [
            "extensions/context-projection/index.ts" # hides stale tool output
            "extensions/custom-compaction/index.ts" # proactive compaction
            "extensions/run-subagent/index.ts" # subagent_* tools
          ];
        }

        # Directory containment and path/bash permission gates. Replaces moonpi,
        # whose guard skipped `bash` entirely (guards.ts: shouldCheckPath covers
        # read/write/edit/grep/find/ls only) and so caught typos, not damage.
        # https://github.com/gotgenes/pi-packages
        "npm:@gotgenes/pi-permission-system"

        # Read-only /plan mode. Replaces moonpi's plan/act modes and the local
        # plan-mode extension, which had been failing to load since pi renamed
        # its npm scope.
        # https://www.npmjs.com/package/@narumitw/pi-plan-mode
        "npm:@narumitw/pi-plan-mode"

        # Reddit JSON research tools + a matching skill: compact evidence packs
        # for opinions, bugs, fixes, comparisons. Needs a session cookie —
        # see reddit-research.json below.
        # ~2,151 tok/request for 7 tools. Kept global deliberately: that is an
        # eighth of what moonpi cost, and scoping it to a project fails silently
        # under `pi -p`, which never prompts for project trust. See dot/pi/CLAUDE.md.
        # https://github.com/SaintNerona/pi-reddit-research
        "npm:pi-reddit-research"
      ];
      description = "Pi packages to declare in settings.json";
    };
  };

  config = lib.mkIf cfg.enable {
    # Remote-oMLX hosts declare models.json here; everyone else gets it from
    # stow + op inject (dot/pi/.pi/agent/models.json.tpl, via `just secrets`).
    home.file.".pi/agent/models.json" = lib.mkIf (cfg.omlxBaseUrl != null) {
      text = builtins.toJSON {
        providers.omlx = {
          baseUrl = cfg.omlxBaseUrl;
          api = "openai-completions";
          apiKey = "no-key-needed"; # oMLX does not authenticate
          compat = {
            supportsDeveloperRole = false;
            supportsReasoningEffort = false;
          };
          models = map (m:
            m
            // {
              cost = {
                input = 0;
                output = 0;
                cacheRead = 0;
                cacheWrite = 0;
              };
            })
          cfg.models;
        };
      };
    };

    # pi-reddit-research needs a Reddit session cookie — Reddit has required
    # auth on its .json endpoints since mid-2026. The cookie is NOT declared
    # here: it expires every few days, and `cookieFile` is re-read before every
    # request, so refreshing it means editing one file — no rebuild, no
    # `just secrets`, no restart. This file holds only the pointer, so a
    # read-only /nix/store symlink is the right shape for it.
    home.file.".pi/agent/reddit-research.json" = {
      text = builtins.toJSON {
        cookieFile = "${config.home.homeDirectory}/.config/pi-reddit-research/cookie.txt";
      };
    };

    # Endpoint for the local web-search extension. No secret in it, so a
    # read-only /nix/store symlink is the right shape — same as reddit-research.json.
    home.file.".pi/agent/searxng.json" = {
      text = builtins.toJSON {inherit (cfg) searxngBaseUrl;};
    };

    home.file.".pi/agent/settings.json" = {
      text = builtins.toJSON {
        defaultProvider = "omlx";
        inherit (cfg) defaultModel;
        lastChangelogVersion = "0.67.6";
        inherit (cfg) packages;
      };
    };

    # Install pi packages (npm/git) on activation. Pi declares packages in
    # settings.json but the actual npm globals and git clones need `pi install`.
    # This runs after writeBoundary so settings.json is already in place.
    # Each install is idempotent — pi skips already-installed packages.
    home.activation.installPiPackages = lib.hm.dag.entryAfter ["writeBoundary"] ''
      if command -v pi &>/dev/null; then
        ${builtins.concatStringsSep "\n        " (map (pkg: ''pi install "${packageSource pkg}" 2>/dev/null || true'') cfg.packages)}
        echo "✓ Pi packages installed"
      fi
    '';
  };
}
