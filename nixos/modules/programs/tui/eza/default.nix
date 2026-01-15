# nixos/modules/programs/tui/eza/default.nix
{...}: {
  programs.eza = {
    enable = true;
    enableZshIntegration = true;
    enableBashIntegration = true;

    extraOptions = [
      "--group-directories-first"
      "--header"
      "--icons"
      "--group"
    ];

    # Note: The integration automatically creates these aliases:
    # ls  -> eza
    # ll  -> eza -l
    # la  -> eza -a
    # lt  -> eza --tree
    # lla -> eza -la
  };
}
