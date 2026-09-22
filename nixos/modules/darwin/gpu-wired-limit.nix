# Raise the Metal "VRAM" ceiling so a local LLM can use more than 75% of RAM.
#
# On Apple Silicon the GPU may only wire a fraction of unified memory. The
# sysctl is `iogpu.wired_limit_mb` and its default is `0`, which does NOT mean
# unlimited — it means "use the built-in default", which is **75% of RAM**. On
# moria's 128 GB that is 96 GB, and oMLX serving Qwen3.6-35B (19 GB) beside
# gpt-oss-120b (59 GB) measured a steady 86-87 GB. Nine gigabytes of headroom,
# into which the KV cache then grows.
#
# Worse, oMLX does not know about the macOS limit. Its own ceiling is
# `max_model_memory: auto`, which resolves to ~84% (107.5 GB here) — ABOVE what
# the kernel will actually wire. So its LRU evicts against a budget it cannot
# spend, and the wall it really hits is one it cannot see.
#
# Raising this so the macOS limit sits ABOVE oMLX's own ceiling puts oMLX's
# memory manager back in charge, which is the coherent arrangement: one limiter,
# and it is the one that understands what it is holding.
#
# **`/etc/sysctl.conf` is ignored on modern macOS.** A root launchd daemon with
# RunAtLoad is the supported way, and it is also why this has to be re-applied
# on every boot rather than written once.
#
# macOS 13 spelled it `debug.iogpu.wired_limit`; 14+ uses `iogpu.wired_limit_mb`.
# Both are set below — an unknown key is a warning, not a failure.
{
  config,
  lib,
  ...
}: let
  cfg = config.custom.system.gpuWiredLimit;
in {
  options.custom.system.gpuWiredLimit = {
    enable = lib.mkEnableOption "raise the Metal wired-memory ceiling for local inference";

    reserveGb = lib.mkOption {
      type = lib.types.ints.positive;
      default = 16;
      description = ''
        Gigabytes left to macOS and everything that is not the GPU. The limit
        becomes (total RAM - this). Every guide that has measured it says to
        keep 8-16 GB back; this host also runs a Desktop app, a browser and a
        terminal, so it takes the cautious end. Below roughly 8 you are betting
        the compositor never needs memory while a model is resident, and the
        failure is a hang rather than an error.
      '';
    };

    minTotalGb = lib.mkOption {
      type = lib.types.ints.positive;
      default = 32;
      description = ''
        Do nothing on a Mac smaller than this. On a 16 GB machine
        (total - reserve) is worse than the 75% default, and this module is for
        hosts that serve models.
      '';
    };
  };

  config = lib.mkIf cfg.enable {
    launchd.daemons.gpu-wired-limit = {
      # Computed at boot from hw.memsize rather than pinned in nix, so the same
      # module is correct on every Mac that imports it. The floor matters: never
      # set a limit LOWER than the 75% the kernel would have picked anyway.
      script = ''
        total_mb=$(( $(/usr/sbin/sysctl -n hw.memsize) / 1048576 ))
        if [ "$total_mb" -lt $(( ${toString cfg.minTotalGb} * 1024 )) ]; then
          echo "$(date -u +%FT%TZ) total ''${total_mb}MB < ${toString cfg.minTotalGb}GB — leaving the default"
          exit 0
        fi
        want=$(( total_mb - ${toString cfg.reserveGb} * 1024 ))
        floor=$(( total_mb * 75 / 100 ))
        [ "$want" -lt "$floor" ] && want=$floor
        /usr/sbin/sysctl -w iogpu.wired_limit_mb=$want 2>/dev/null \
          || /usr/sbin/sysctl -w debug.iogpu.wired_limit=$want 2>/dev/null \
          || { echo "$(date -u +%FT%TZ) could not set either sysctl"; exit 1; }
        echo "$(date -u +%FT%TZ) iogpu.wired_limit_mb=$want of ''${total_mb}MB (reserved ${toString cfg.reserveGb}GB)"
      '';
      serviceConfig = {
        RunAtLoad = true;
        # One shot. It sets a kernel parameter and exits; KeepAlive would
        # respawn it forever.
        KeepAlive = false;
        StandardOutPath = "/var/log/gpu-wired-limit.log";
        StandardErrorPath = "/var/log/gpu-wired-limit.log";
      };
    };
  };
}
