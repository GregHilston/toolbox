# nixos/modules/programs/tui/starship/default.nix
{
  config,
  lib,
  ...
}: {
  programs.starship = {
    enable = true;
    enableZshIntegration = true;
    enableBashIntegration = true;

    settings = {
      # Clean, minimal prompt with useful context
      format = lib.concatStrings [
        "$username"
        "$hostname"
        "$directory"
        "$git_branch"
        "$git_status"
        "$nix_shell"
        "$line_break"
        "$character"
      ];

      character = {
        success_symbol = "[❯](bold green)";
        error_symbol = "[✗](bold red)";
      };

      directory = {
        truncation_length = 3;
        truncate_to_repo = true;
        style = "bold cyan";
      };

      git_branch = {
        symbol = " ";
        style = "bold purple";
      };

      git_status = {
        style = "bold yellow";
        conflicted = "🏳";
        ahead = "⇡\${count}";
        behind = "⇣\${count}";
        diverged = "⇕⇡\${ahead_count}⇣\${behind_count}";
        untracked = "?";
        stashed = "$";
        modified = "!";
        staged = "+";
        renamed = "»";
        deleted = "✘";
      };

      nix_shell = {
        symbol = " ";
        format = "via [$symbol$state]($style) ";
        style = "bold blue";
      };

      username = {
        show_always = false;
        format = "[$user]($style)@";
        style_user = "bold green";
      };

      hostname = {
        ssh_only = true;
        format = "[$hostname]($style) ";
        style = "bold green";
      };
    };
  };
}
