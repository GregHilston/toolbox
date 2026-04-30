{
  config,
  lib,
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
      default = "";
      description = "API key for oMLX. Load from env var: builtins.getEnv \"OMLX_API_KEY\"";
    };

    omlxBaseUrl = lib.mkOption {
      type = lib.types.str;
      default = "http://localhost:8000/v1";
      description = "Base URL for oMLX server";
    };

    models = lib.mkOption {
      type = lib.types.listOf (lib.types.attrs);
      default = [
        {
          id = "Qwen3.6-35B-A3B-8bit";
          name = "Qwen 3.6 35B A3B (thinking, 262k ctx, 81k max, heavy)";
          contextWindow = 262144;
          maxTokens = 81920;
          input = ["text"];
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
          input = ["text"];
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
          input = ["text"];
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
      };
    };
  };
}
