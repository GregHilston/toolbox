{ config, pkgs, ... }:

let
  user = "ghilston";
  home-manager = builtins.fetchTarball "https://github.com/nix-community/home-manager/archive/release-24.05.tar.gz";
  lazyvim = pkgs.fetchTarball {
    url = "https://github.com/LazyVim/starter/archive/refs/heads/main.tar.gz";
    sha256 = "13ajrzgw9i0nna88l3bnfbf7m3nb889zgzrbyldd6ls82jsbf7lw";
  };
in
{
  imports =
  [
    (import "${home-manager}/nixos")
  ];

  home-manager.users.${user} = {
    home.username = user;
    home.stateVersion = "24.05";

    home.packages = with pkgs; [
    #   kdeApplications.kate
      bitwarden
      dmenu
      obsidian
      slack
      spotify
      vlc
      vscode
      firefox
    ];

    programs.zsh = {
      enable = true;
      enableCompletion = true;
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
          { name = "zsh-users/zsh-autosuggestions"; }

          # Reminds you to use commands you've forgotten
          { name = "MichaelAquilina/zsh-you-should-use"; }

          # Fast syntax highlighting for Zsh
          { name = "zdharma-continuum/fast-syntax-highlighting"; }

          # Better history search
          { name = "zsh-users/zsh-history-substring-search"; }

          # Auto-pairing of quotes, brackets, etc.
          { name = "hlissner/zsh-autopair"; }

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
        ll = "ls -l";
        test = "sudo nixos-rebuild test";
        edit = "nvim /home/${user}/Git/toolbox/nixos/configuration.nix";
        update = "sudo cp  /home/${user}/Git/toolbox/nixos/configuration.nix /etc/nixos && sudo nixos-rebuild switch";
        gitCommitUndo = "git reset --soft HEAD\\^";
      };
      history.size = 10000;
      history.path = "/home/${user}/.zsh_history";
    };

    programs.neovim = {
      enable = true;
      extraConfig = ''
        call plug#begin('~/.local/share/nvim/plugged')
        Plug 'preservim/nerdtree'
        " Add other Plug plugins here
        call plug#end()
      '';
    };

    # Set location for nvim config to DotFiles repo in home directory
    home.file.".config/nvim" = {
      source = lazyvim;
    };

    programs.git = {
      enable = true;
      userName  = "GregHilston";
      userEmail = "Gregory.Hilston@gmail.com";
      };

    # # Set location for zsh config
    # home.file.".zshrc" = {
    #   source = /home/${user}/Git/toolbox/dot/zshrc;
    # };
  };
}
