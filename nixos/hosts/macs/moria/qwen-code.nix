{lib, ...}: let
  qwenSettings = builtins.toJSON {
    modelProviders.openai = [
      {
        id = "Qwen3.6-27B-8bit";
        name = "Qwen3.6 27B 8bit (omlx)";
        baseUrl = "http://localhost:8000/v1";
        description = "Local model via omlx";
      }
    ];
    security.auth.selectedType = "openai";
    model.name = "Qwen3.6-27B-8bit";
  };
in {
  # Point qwen-code at the local omlx inference server running on moria.
  home.activation.qwenCodeSetup = lib.hm.dag.entryAfter ["writeBoundary"] ''
    mkdir -p "$HOME/.qwen"
    echo '${qwenSettings}' > "$HOME/.qwen/settings.json"
  '';
}
