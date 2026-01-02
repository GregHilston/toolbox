{
  pkgs,
  inputs,
  ...
}: {
  programs.git = {
    enable = true;

    settings = {
      user = {
        name = "GregHilston";
        email = "Gregory.Hilston@gmail.com";
      };

      alias = {
        # Quick shortcuts
        st = "status";
        co = "checkout";
        br = "branch";
        ci = "commit";

        # Useful commands
        cleanup = "!git branch --merged | grep -v '\\*\\|master\\|main\\|develop' | xargs -n 1 -r git branch -d";
        unstage = "reset HEAD --";
        last = "log -1 HEAD";

        # Pretty log views
        lg = "log --graph --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' --abbrev-commit --date=relative";
        lga = "log --graph --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' --abbrev-commit --date=relative --all";

        # Repository root
        root = "rev-parse --show-toplevel";
      };
    };
  };

  # Delta: Syntax-highlighting diff viewer
  # Automatically integrates with git diff, show, and log commands
  programs.delta = {
    enable = true;

    # Auto-configure git to use delta as pager
    enableGitIntegration = true;

    options = {
      line-numbers = true; # Show line numbers in diffs
      navigate = true; # Use n/N to jump between files
      side-by-side = false; # Unified diff (change to true for split view)
      dark = true; # Dark mode color scheme
      syntax-theme = "Nord"; # Syntax highlighting theme
      keep-plus-minus-markers = true; # Keep +/- markers visible
    };
  };
}
