# KDE Plasma desktop stack: X server, SDDM, Plasma 6, PipeWire, and the
# 1Password GUI. Gated behind custom.desktop.enable so headless hosts don't
# inherit a full desktop environment. The default follows the per-host
# vars.enableGui flag (which also drives the GUI packages in modules/home).
{
  config,
  lib,
  vars,
  ...
}: {
  options.custom.desktop.enable = lib.mkOption {
    type = lib.types.bool;
    default = vars.enableGui or false;
    description = "Enable the KDE Plasma desktop stack (SDDM, Plasma 6, PipeWire, 1Password GUI).";
  };

  config = lib.mkIf config.custom.desktop.enable {
    services = {
      xserver.enable = true;
      displayManager.sddm.enable = true;
      desktopManager.plasma6.enable = true;

      xserver.xkb = {
        layout = "us";
        variant = "";
      };

      pipewire = {
        enable = true;
        alsa.enable = true;
        alsa.support32Bit = true;
        pulse.enable = true;
      };
    };

    security.rtkit.enable = true;

    # 1Password GUI (desktop app + polkit integration). The CLI
    # (programs._1password) stays in modules/common for headless hosts.
    programs._1password-gui = {
      enable = true;
      polkitPolicyOwners = [vars.user.name];
    };
  };
}
