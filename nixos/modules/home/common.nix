# Identity + bootstrap shared by every home-manager profile in this repo:
# the NixOS workstation (./default.nix), the Darwin workstation
# (../darwin/home.nix), and rohan's writerdeck (hosts/pcs/rohan).
#
# Deliberately tiny — only the facts that hold for every user profile on every
# host. Anything with a package cost belongs in ./workstation.nix (the NixOS +
# Darwin baseline) or in the host's own profile, so rohan can take this layer
# without inheriting a workstation's closure.
{
  pkgs,
  vars,
  ...
}: {
  home = {
    username = vars.user.name;

    homeDirectory =
      if pkgs.stdenv.hostPlatform.isDarwin
      then "/Users/${vars.user.name}"
      else "/home/${vars.user.name}";

    # https://nixos.wiki/wiki/FAQ/When_do_I_update_stateVersion
    stateVersion = "24.05";
  };

  programs.home-manager.enable = true;
}
