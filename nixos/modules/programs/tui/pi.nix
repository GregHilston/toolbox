{
  config,
  lib,
  pkgs,
  ...
}: let
  cfg = config.custom.programs.pi;
in {
  options.custom.programs.pi = {
    enable = lib.mkEnableOption "pi (pi-mono coding agent)";

    defaultModel = lib.mkOption {
      type = lib.types.str;
      default = "Qwen3.6-35B-A3B-8bit";
      description = "Default model to use";
    };

    apiKey = lib.mkOption {
      type = lib.types.str;
      default = "local";
      description = "API key for oMLX. Pi requires a non-empty string even if the server doesn't enforce auth. Load from env var: builtins.getEnv \"OMLX_API_KEY\"";
    };

    omlxBaseUrl = lib.mkOption {
      type = lib.types.str;
      default = "http://localhost:8000/v1";
      description = "Base URL for oMLX server";
    };

    # Packages installed via `pi install`. Pi resolves these at runtime.
    # Git-based packages are cloned to ~/.pi/agent/git/; npm packages go to
    # the global node_modules. Local extensions (plan-mode) live in
    # ~/.pi/agent/extensions/ managed by stow from dot/pi/.
    packages = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [
        # Rust-powered frecency-ranked, fuzzy, git-aware file search
        # https://github.com/dmtrKovalenko/fff
        "npm:@ff-labs/pi-fff"

        # Context management: context-projection (hides stale tool output),
        # context-overflow (proactive compaction), custom-compaction, subagents
        # https://github.com/n-r-w/pi-agent-suite
        "npm:pi-agent-suite"

        # Read-before-write enforcement, directory containment, work modes
        # https://github.com/galatolofederico/moonpi
        "https://github.com/galatolofederico/moonpi"
      ];
      description = "Pi packages to declare in settings.json";
    };

    models = lib.mkOption {
      type = lib.types.listOf (lib.types.attrs);
      default = [
        {
          id = "Qwen3.6-35B-A3B-8bit";
          name = "Qwen 3.6 35B A3B (thinking, 262k ctx, 81k max, heavy)";
          contextWindow = 262144;
          maxTokens = 81920;
          # Qwen3.6 supports vision — enable so Pi can send screenshots
          # https://www.reddit.com/r/LocalLLaMA/comments/1ss9pku/
          input = ["text" "image"];
          cost = {
            input = 0;
            output = 0;
            cacheRead = 0;
            cacheWrite = 0;
          };
        }
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
        {
          id = "gemma-4-26b-a4b-it-4bit";
          name = "Gemma 4 26B A4B (summarization, 256k ctx, fast)";
          contextWindow = 262144;
          maxTokens = 32768;
          input = ["text" "image"];
          cost = {
            input = 0;
            output = 0;
            cacheRead = 0;
            cacheWrite = 0;
          };
        }
        {
          id = "gpt-oss-120b-heretic-v2-mxfp4-q8-hi-mlx";
          name = "GPT-OSS 120B Heretic v2 (local)";
          contextWindow = 32768;
          maxTokens = 32768;
          input = ["text"];
          cost = {
            input = 0;
            output = 0;
            cacheRead = 0;
            cacheWrite = 0;
          };
        }
      ];
      description = "List of available models";
    };
  };

  config = lib.mkIf cfg.enable {
    home.file.".pi/agent/models.json" = {
      text = builtins.toJSON {
        providers = {
          omlx = {
            baseUrl = cfg.omlxBaseUrl;
            api = "openai-completions";
            apiKey = cfg.apiKey;
            compat = {
              supportsDeveloperRole = false;
              supportsReasoningEffort = false;
            };
            models = cfg.models;
          };
        };
      };
    };

    home.file.".pi/agent/settings.json" = {
      text = builtins.toJSON {
        defaultProvider = "omlx";
        defaultModel = cfg.defaultModel;
        lastChangelogVersion = "0.67.6";
        packages = cfg.packages;
      };
    };

    # Install pi packages (npm/git) on activation. Pi declares packages in
    # settings.json but the actual npm globals and git clones need `pi install`.
    # This runs after writeBoundary so settings.json is already in place.
    # Each install is idempotent — pi skips already-installed packages.
    home.activation.installPiPackages = lib.hm.dag.entryAfter ["writeBoundary"] ''
      if command -v pi &>/dev/null; then
        ${builtins.concatStringsSep "\n        " (map (pkg: ''pi install "${pkg}" 2>/dev/null || true'') cfg.packages)}
        echo "✓ Pi packages installed"
      fi
    '';
  };
}
