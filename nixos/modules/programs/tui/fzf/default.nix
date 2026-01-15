# nixos/modules/programs/tui/fzf/default.nix
{...}: {
  programs.fzf = {
    enable = true;
    enableZshIntegration = true;
    enableBashIntegration = true;

    # Default command uses fd for faster file searching
    defaultCommand = "fd --type f --hidden --follow --exclude .git";

    # Keybindings:
    # Ctrl+T: Paste selected files/directories
    # Ctrl+R: Paste selected command from history
    # Alt+C: cd into selected directory

    defaultOptions = [
      "--height 40%"
      "--layout=reverse"
      "--border"
      "--inline-info"
      "--color=fg:#d0d0d0,bg:#121212,hl:#5f87af"
      "--color=fg+:#d0d0d0,bg+:#262626,hl+:#5fd7ff"
      "--color=info:#afaf87,prompt:#d7005f,pointer:#af5fff"
      "--color=marker:#87ff00,spinner:#af5fff,header:#87afaf"
    ];
  };
}
