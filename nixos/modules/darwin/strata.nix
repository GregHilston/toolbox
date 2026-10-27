{
  config,
  lib,
  vars,
  ...
}: let
  cfg = config.custom.services.strata;
  home = "/Users/${vars.user.name}";
in {
  options.custom.services.strata = {
    enable = lib.mkEnableOption ''
      Strata (https://github.com/Niko1221/Strata) serving Qwen3.8-Flash-Next,
      the heavy local model, as a launchd user agent. Nix owns the agent; the
      install itself (pinned checkout, Metal build, model) is `just strata-setup`
    '';
    listen = lib.mkOption {
      type = lib.types.str;
      default = vars.networking.hosts.${config.networking.hostName}.tailscale;
      defaultText = lib.literalExpression "vars.networking.hosts.\${config.networking.hostName}.tailscale";
      description = "Address to bind. The tailnet address: home-lab's LiteLLM reaches it there.";
    };
    port = lib.mkOption {
      type = lib.types.port;
      default = 8080;
    };
    dir = lib.mkOption {
      type = lib.types.str;
      default = "${home}/Git/strata";
      description = "The checkout bin/strata-setup.sh manages (STRATA_DIR).";
    };
  };

  config = lib.mkIf cfg.enable {
    launchd.user.agents.strata.serviceConfig = {
      # oMLX's key, so the gateway needs no second secret.
      ProgramArguments = [
        "/bin/sh"
        "-c"
        ''
          STRATA_API_KEY=$(/usr/bin/jq -r .auth.api_key ${home}/.omlx/settings.json) exec \
            ${cfg.dir}/.venv/bin/python -u ${cfg.dir}/serve/server.py --engine strata \
            --config ${cfg.dir}/strata.json --host ${cfg.listen} --port ${toString cfg.port}
        ''
      ];
      WorkingDirectory = cfg.dir;
      RunAtLoad = true;
      # Also covers boot: the bind fails until Tailscale has the address up.
      KeepAlive = true;
      # Quiet retries until `just strata-setup` has built it.
      ThrottleInterval = 30;
      StandardOutPath = "${home}/Library/Logs/strata.log";
      StandardErrorPath = "${home}/Library/Logs/strata.log";
    };
  };
}
