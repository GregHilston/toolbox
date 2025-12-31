{
  vars,
  pkgs,
  ...
}: {
  programs.zsh = {
    enable = true;
    enableCompletion = true;

    # Enable VS Code shell integration (works in tmux too)
    initExtra = ''
      # Check for VS Code via Remote-SSH (VSCODE_IPC_HOOK_CLI) or native terminal (TERM_PROGRAM)
      if [[ -n "$VSCODE_IPC_HOOK_CLI" ]] || [[ "$TERM_PROGRAM" == "vscode" ]]; then
        if command -v code &> /dev/null; then
          . "$(code --locate-shell-integration-path zsh 2>/dev/null)" 2>/dev/null || true
        fi
      fi
    '';
    # syntaxHighlighting.enable = true;
    zplug = {
      enable = true;
      plugins = [
        # Fast jump around
        # { name = "agkozak/zsh-z"; }

        # A collection of utility functions for Zsh
        # { name = "belak/zsh-utils"; }

        # Adds vi mode to Zsh, allowing modal editing
        # { name = "jeffreytse/zsh-vi-mode"; }

        # Suggests commands as you type based on history and completions
        {name = "zsh-users/zsh-autosuggestions";}

        # Reminds you to use commands you've forgotten
        {name = "MichaelAquilina/zsh-you-should-use";}

        # Fast syntax highlighting for Zsh
        {name = "zdharma-continuum/fast-syntax-highlighting";}

        # Better history search
        {name = "zsh-users/zsh-history-substring-search";}

        # Auto-pairing of quotes, brackets, etc.
        {name = "hlissner/zsh-autopair";}

        # Directory listings with colors
        # { name = "supercrabtree/k"; }

        # Visual mode for Zsh
        # { name = "b4b4r07/zsh-vimode-visual"; }
      ];
    };
    oh-my-zsh = {
      enable = true;
      plugins = [
        "git"
        "docker"
      ];
    };

    shellAliases = {
      vim = "nvim";
      v = "nvim";
      e = "exit";
      c = "clear";
      cs = "sudo nix-store --gc";
      lg = "lazygit";
      # ll provided by eza integration
      gitCommitUndo = "git reset --soft HEAD\\^";
      cat = "bat";
      # Copies a file's contents into the system's clipboard.
      clip = "xclip -sel clip <";
      # nix garbage collect
      ncg = "nix-collect-garbage --delete-older-than 3d && sudo nix-collect-garbage -d && sudo /run/current-system/bin/switch-to-configuration boot";
      nc = "nix flake check";
      nt = "nix flake test";
      opts = "man home-configuration.nix";
      cleanup = "nh clean all";

      # Remind to use modern alternatives
      cd = "echo '💡 Tip: Use \"z\" for smart directory jumping! (or use \"builtin cd\" for traditional cd)' && builtin cd";
    };
    history.size = 10000;
    history.path = "/home/${vars.user.name}/.zsh_history";
  };
}
