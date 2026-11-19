# Never sleep on AC, lid closed or not; sleep normally on battery.
#
# Caffeinate and keep-awake apps only block idle sleep. With the lid closed,
# macOS sleeps the moment the last external display goes ("Clamshell Sleep"),
# even on AC: moria slept on 2026-11-19 when its monitor was switched off.
# `pmset disablesleep` is the only switch that stops that, and it has no
# per-power-source form, so a root daemon flips it to match the power source.
{
  config,
  lib,
  ...
}: let
  cfg = config.custom.system.awakeOnAc;
in {
  options.custom.system.awakeOnAc = {
    enable = lib.mkEnableOption "never sleep on AC power, even in clamshell with no display";
  };

  config = lib.mkIf cfg.enable {
    launchd.daemons.awake-on-ac = {
      script = ''
        if /usr/bin/pmset -g batt | /usr/bin/grep -q "'AC Power'"; then want=1; else want=0; fi
        # pmset prints no SleepDisabled line while it is 0.
        have=$(/usr/bin/pmset -g | /usr/bin/awk '/SleepDisabled/ {print $2}')
        if [ "''${have:-0}" != "$want" ]; then
          /usr/bin/pmset -a disablesleep "$want"
          echo "$(date -u +%FT%TZ) disablesleep $want"
        fi
      '';
      serviceConfig = {
        RunAtLoad = true;
        # Unplugging with the lid closed can stay awake up to this long.
        StartInterval = 30;
        StandardOutPath = "/var/log/awake-on-ac.log";
        StandardErrorPath = "/var/log/awake-on-ac.log";
      };
    };
  };
}
