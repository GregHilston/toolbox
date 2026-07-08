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
    openssh.authorizedKeys.keys = [
      "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCmEoG6aAA559ZIVc4citslV5TxVTb3tbheaSTB/+bo1uOi/IDVS/yEgDqObY2KvP7uqeNqn10diVoe0Pg4yLiFTuNriFA6aPmhs00DjazttGj8WyFDOJnBIg1NL9BlewvkxlSXa/LsWfN8JanZ1Cwknff8jxxbm+s1CxV8+XWWK4MHsfHixfD69UP437cJ9QuomKFrWZ4A+s4SUHfKVknFn0xDgclay3/h6cAdc9+rlYe73UY6AzeqgKlOxL1S1NNn2TIyhmBQm32xhsW++LLpG/4jv1+pgRHeghmJYPk1+ZeGkGRi/oRSibMActa960WBccHOMxCTVDhF/Rkyw4RoMCU/gU3zFY8Nm92xM34+SU23Sf1xdP6Gs2/raQIf49bVOkGNZXtmHBh+dvnTBxmgXcyHHoJGLPYy/Ct/IYYoeRn6lRxiBSidu0kk9hwL0JqF75a7wDlHXN4hWLXvma4RKrIgGt8pJGsjjIa1bWSKKUowuLgm56PCDC0Dxa95fBE= moria (macbook pro)"
    ];
  };
}
