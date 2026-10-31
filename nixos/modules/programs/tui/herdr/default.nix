# nixos/modules/programs/tui/herdr/default.nix
#
# Config only. The binary comes from Homebrew on Macs and systemPackages on
# NixOS. Config is stow-managed from dot/herdr.
{
  lib,
  pkgs,
  ...
}: {
  home.activation.stowHerdr = lib.hm.dag.entryAfter ["writeBoundary"] ''
    DOTFILES="$HOME/Git/toolbox/dot"
    if [ -d "$DOTFILES/herdr" ]; then
      cd "$DOTFILES"
      # --no-folding: Herdr keeps sockets, logs and session.json in
      # ~/.config/herdr, which must not land in this repo's working tree.
      ${pkgs.stow}/bin/stow -v --no-folding -t "$HOME" herdr 2>&1 \
        || echo "stow: conflict for herdr: remove ~/.config/herdr/config.toml then re-run home-manager"
    fi
  '';
}
