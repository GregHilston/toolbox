# nixos/modules/programs/tui/zoxide/default.nix
{
  config,
  lib,
  ...
}: {
  programs.zoxide = {
    enable = true;
    enableZshIntegration = true;
    enableBashIntegration = true;

    # Use 'z' command for jumping to directories
    # Usage: z <partial-path>  # Jump to most frecent matching directory
    #        zi                 # Interactive selection with fzf
    options = ["--cmd" "z"];
  };
}
