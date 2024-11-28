{ pkgs, ... }: {
  programs.vscode = {
    enable = true;
    package = pkgs.vscode;
    enableUpdateCheck = false;
    enableExtensionUpdateCheck = false;
    mutableExtensionsDir = false;

    # Add extensions that are in Nix OS package manager
    extensions = with pkgs.vscode-extensions; [
      # Microsoft
      ms-vscode-remote.remote-ssh
      ms-vscode-remote.remote-ssh-edit
      ms-azuretools.vscode-docker

      # tools
      vscodevim.vim
      vspacecode.whichkey

      # languages
      golang.go
      # ms-python.python
      jnoortheen.nix-ide
      golang.go
      mikestead.dotenv
      sumneko.lua

      # utility
      alefragnani.bookmarks
      gruntfuggly.todo-tree
      christian-kohler.path-intellisense
      streetsidesoftware.code-spell-checker

      # UI
      usernamehw.errorlens
      aaron-bond.better-comments
      catppuccin.catppuccin-vsc 
      pkief.material-icon-theme
    ] ++ pkgs.vscode-utils.extensionsFromVscodeMarketplace [
      # Add extensions that aren't in nixpkgs but are in the marketplace
      
      # {
      #   name = "remote-ssh";
      #   publisher = "ms-vscode-remote";
      #   version = "0.107.2024030816";
      #   sha256 = "sha256-yoursha256here"; # Replace with actual SHA
      # }
    ];

    userSettings = {
      "vim.handleKeys" = {
        # Disables the usage of `CTRL + p` for Vim, so we can let VSCode use that for opening the file searcher
        "<C-p>" = false;
        # Disables the usage of `CTRL + p` for Vim, so we can let VSCode use that for closing a file
        "<C-w>" = false;
        # Disables the usage of `CTRL + f` for Vim, so we can let VSCode use that for searching a file
        "<C-f>" = false;
        # Disables the usage of `CTRL + n` for Vim, so we can let VSCode use that for opening a file
        "<C-n>" = false;
        # Disables the usage of `CTRL + b` for Vim, so we can let VSCode use that for toggling the file explorer
        "<C-b>" = false;
      };
    };

    keybindings = [
    ];
  };
}
