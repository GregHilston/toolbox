{
  pkgs,
  inputs,
  ...
}: {
  programs.git = {
    enable = true;
    userName = "GregHilston";
    userEmail = "Gregory.Hilston@gmail.com";

    aliases = {
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
}
