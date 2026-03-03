# nixos/modules/programs/tui/atuin/default.nix
{...}: {
  programs.atuin = {
    enable = true;
    enableZshIntegration = true;
    enableBashIntegration = true;

    # Keybindings:
    # Up arrow: Open TUI to search through shell history
    # Ctrl+R: Also opens the history search TUI

    settings = {
      # Search mode: prefix, fulltext, fuzzy, or skim
      search_mode = "fuzzy";
      # Filter mode when pressing up arrow: global, host, session, directory
      filter_mode_shell_up_key_binding = "host";
      # Style of the TUI: auto, full, or compact
      style = "auto";
      # Show a preview of the full command
      show_preview = true;
      # Disable automatic sync (opt-in later if wanted)
      auto_sync = false;
    };
  };
}
