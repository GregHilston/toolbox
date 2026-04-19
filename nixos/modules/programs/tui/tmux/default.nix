# nixos/modules/programs/tui/tmux/default.nix
{pkgs, ...}: {
  programs.tmux = {
    enable = true;

    # Use zsh as the default shell in tmux
    shell = "${pkgs.zsh}/bin/zsh";

    # Start window and pane numbering at 1 instead of 0
    baseIndex = 1;

    # Reduce escape time for faster vim response
    escapeTime = 10;

    # Increase scrollback history
    historyLimit = 10000;

    # Vi mode for copy mode (use vi keybindings)
    keyMode = "vi";

    # Enable mouse support for scrolling and pane selection
    mouse = true;

    # Enable 256 color support
    terminal = "screen-256color";

    extraConfig = ''
      # Enable true color and proper terminal capabilities
      set -g default-terminal "tmux-256color"
      set -ga terminal-overrides ",*256col*:Tc"
      set -ga terminal-overrides ",xterm-256color:RGB"

      # Better split keybindings (more intuitive)
      # | for vertical split, - for horizontal split
      unbind '"'
      unbind %
      bind | split-window -h -c "#{pane_current_path}"
      bind - split-window -v -c "#{pane_current_path}"

      # Vim-aware pane navigation (seamless vim/tmux navigation)
      # These allow Ctrl+h/j/k to navigate between tmux panes AND vim splits
      # NOTE: C-l is intentionally excluded to preserve the standard terminal
      # behavior of clearing the screen. Use prefix + arrow keys or prefix + o
      # to navigate to the right pane instead.
      is_vim="ps -o state= -o comm= -t '#{pane_tty}' | grep -iqE '^[^TXZ ]+ +(\\S+\\/)?g?(view|l?n?vim?x?|fzf)(diff)?$'"
      bind-key -n 'C-h' if-shell "$is_vim" 'send-keys C-h' 'select-pane -L'
      bind-key -n 'C-j' if-shell "$is_vim" 'send-keys C-j' 'select-pane -D'
      bind-key -n 'C-k' if-shell "$is_vim" 'send-keys C-k' 'select-pane -U'

      # Vim-aware pane navigation in copy mode (C-l excluded, see above)
      bind-key -T copy-mode-vi 'C-h' select-pane -L
      bind-key -T copy-mode-vi 'C-j' select-pane -D
      bind-key -T copy-mode-vi 'C-k' select-pane -U

      # Resize panes with arrow keys
      bind -n S-Left resize-pane -L 5
      bind -n S-Right resize-pane -R 5
      bind -n S-Down resize-pane -D 5
      bind -n S-Up resize-pane -U 5

      # Reload config with prefix + r
      bind r source-file ~/.config/tmux/tmux.conf \; display "Config reloaded!"

      # Enable focus events (needed for some vim plugins)
      set -g focus-events on

      # CSI-u extended keys (required for pi and other modern TUI apps)
      set -g extended-keys on
      set -g extended-keys-format csi-u

      # Undercurl support (for zsh-autosuggestions styling)
      set -as terminal-overrides ',*:Smulx=\E[4::%p1%dm'
      set -as terminal-overrides ',*:Setulc=\E[58::2::%p1%{65536}%/%d::%p1%{256}%/%{255}%&%d::%p1%{255}%&%d%;m'
    '';
  };
}
