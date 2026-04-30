{
  config,
  lib,
  ...
}: let
  cfg = config.custom.programs.opencode;
in {
  options.custom.programs.opencode = {
    enable = lib.mkEnableOption "opencode (AI coding agent for the terminal)";

    defaultModel = lib.mkOption {
      type = lib.types.str;
      default = "Qwen3.6-35B-A3B-8bit";
      description = "Default model to use";
    };

    apiKey = lib.mkOption {
      type = lib.types.str;
      default = "{env:OMLX_API_KEY}";
      description = "API key for oMLX. Uses OpenCode's runtime env var substitution so the real key never enters VCS. Set OMLX_API_KEY in your shell (direnv handles this via nixos/.envrc).";
    };

    omlxBaseUrl = lib.mkOption {
      type = lib.types.str;
      default = "http://localhost:8000/v1";
      description = "Base URL for oMLX server";
    };
  };

  config = lib.mkIf cfg.enable {
    xdg.configFile."opencode/opencode.json" = {
      text = builtins.toJSON {
        "$schema" = "https://opencode.ai/config.json";
        model = cfg.defaultModel;
        provider = {
          omlx = {
            npm = "@ai-sdk/openai-compatible";
            name = "oMLX (local)";
            options = {
              baseURL = cfg.omlxBaseUrl;
              apiKey = cfg.apiKey;
            };
            models = {
              "Qwen3.6-35B-A3B-8bit" = {
                name = "Qwen 3.6 35B A3B 8-bit (oMLX)";
                limit = {
                  context = 262144;
                  output = 81920;
                };
              };
            };
          };
        };
      };
    };
  };
}
