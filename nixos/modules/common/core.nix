# Minimal cross-host NixOS baseline: nix settings, networking, locale, and the
# primary user. Small enough to import even on the writerdeck (rohan), which
# deliberately skips the desktop-heavy modules/common.
{
  pkgs,
  vars,
  ...
}: {
  nix.settings.experimental-features = ["nix-command" "flakes"];

  networking.networkmanager.enable = true;

  time.timeZone = vars.system.timeZone;

  i18n = {
    defaultLocale = vars.system.locale;
    extraLocaleSettings = {
      LC_ADDRESS = vars.system.locale;
      LC_IDENTIFICATION = vars.system.locale;
      LC_MEASUREMENT = vars.system.locale;
      LC_MONETARY = vars.system.locale;
      LC_NAME = vars.system.locale;
      LC_NUMERIC = vars.system.locale;
      LC_PAPER = vars.system.locale;
      LC_TELEPHONE = vars.system.locale;
      LC_TIME = vars.system.locale;
    };
  };

  users.users.${vars.user.name} = {
    initialPassword = "password";
    isNormalUser = true;
    description = vars.user.fullName;
    extraGroups = ["networkmanager" "wheel"];
    ignoreShellProgramCheck = true;
    shell = pkgs.${vars.user.packages.shell};
    openssh.authorizedKeys.keys = vars.user.authorizedKeys;
  };
}
