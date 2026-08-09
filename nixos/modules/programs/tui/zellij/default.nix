# nixos/modules/programs/tui/zellij/default.nix
#
# Installed but deliberately not auto-attached — used manually alongside tmux,
# which owns the default multiplexer role (see ../tmux).
_: {
  programs.zellij.enable = true;
}
