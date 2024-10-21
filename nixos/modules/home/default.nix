{ inputs, outputs, lib, config, pkgs, vars, ... }:

{
  imports = [
    inputs.home-manager.nixosModules.home-manager
    # ../programs/tui/neovim
    # ../programs/gui/alacritty
  ];

  nixpkgs = {
    config = {
      allowUnfree = true;
      allowUnfreePredicate = _: true;
    };
  };

  home-manager = {
    useGlobalPkgs = true;
    useUserPackages = true;
    extraSpecialArgs = { inherit inputs vars; };
    users.${vars.user} = {
      home = {
        username = "${vars.user}";
        homeDirectory = "/home/${vars.user}";

        packages = with pkgs; [
          bitwarden
          dmenu
          obsidian
          slack
          spotify
          vlc
          vscode
          firefox
        ];

        # https://nixos.wiki/wiki/FAQ/When_do_I_update_stateVersion
        stateVersion = "24.05";
      };

      programs = {
        home-manager.enable = true;

        zsh = {
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
            gitCommitUndo = "git reset --soft HEAD\\^";
          };
          history.size = 10000;
          history.path = "/home/${vars.user}/.zsh_history";
        };

        neovim = {
          enable = true;
          defaultEditor = true;
          viAlias = true;
          vimAlias = true;
        };

        git = {
          enable = true;
          userName  = "GregHilston";
          userEmail = "Gregory.Hilston@gmail.com";
        };
      };      
    };
  };
}
