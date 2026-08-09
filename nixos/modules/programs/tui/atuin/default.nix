# nixos/modules/programs/tui/atuin/default.nix
#
# `settings` below is real config — it renders ~/.config/atuin/config.toml.
# The shell hook (up-arrow / Ctrl+R) lives in ../zsh; see that module's header.
_: {
  programs.atuin = {
    enable = true;

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
