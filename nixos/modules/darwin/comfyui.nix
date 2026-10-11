{
  config,
  lib,
  vars,
  ...
}: let
  cfg = config.custom.services.comfyui;
  home = "/Users/${vars.user.name}";
in {
  options.custom.services.comfyui = {
    enable = lib.mkEnableOption ''
      ComfyUI (https://github.com/Comfy-Org/ComfyUI), node-based image
      generation, as a launchd user agent. Nix owns the agent; the install
      itself (clone, venv, models) is `just comfyui-setup`
    '';
    listen = lib.mkOption {
      type = lib.types.str;
      default = vars.networking.hosts.${config.networking.hostName}.tailscale;
      description = ''
        Address to bind. The tailnet address by default: ComfyUI has no
        authentication, and home-lab's Caddy reaches it over the tailnet.
      '';
    };
    port = lib.mkOption {
      type = lib.types.port;
      default = 8188;
    };
    dir = lib.mkOption {
      type = lib.types.str;
      default = "${home}/ComfyUI";
      description = "The git clone bin/comfyui-setup.sh manages (COMFYUI_DIR).";
    };
  };

  config = lib.mkIf cfg.enable {
    launchd.user.agents.comfyui.serviceConfig = {
      ProgramArguments = [
        "${cfg.dir}/.venv/bin/python"
        "-u"
        "${cfg.dir}/main.py"
        "--listen"
        cfg.listen
        "--port"
        (toString cfg.port)
        "--enable-manager"
      ];
      WorkingDirectory = cfg.dir;
      EnvironmentVariables = {
        # The Manager installs custom nodes with uv, which lives in one of these.
        PATH = "${home}/.local/bin:/etc/profiles/per-user/${vars.user.name}/bin:/opt/homebrew/bin:/usr/bin:/bin";
        # Custom nodes hit ops MPS lacks; fall back to CPU instead of failing.
        PYTORCH_ENABLE_MPS_FALLBACK = "1";
      };
      RunAtLoad = true;
      # Also covers boot: the bind fails until Tailscale has the address up.
      KeepAlive = true;
      # Quiet retries until `just comfyui-setup` has created the venv.
      ThrottleInterval = 30;
      StandardOutPath = "${home}/Library/Logs/comfyui.log";
      StandardErrorPath = "${home}/Library/Logs/comfyui.log";
    };
  };
}
