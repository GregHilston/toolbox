{ pkgs, ... }: {
  programs.vscode = {
    enable = true;
    package = pkgs.vscode;
    enableUpdateCheck = false;
    enableExtensionUpdateCheck = false;
    mutableExtensionsDir = true;

    # Add extensions that are in Nix OS package manager
    extensions = with pkgs.vscode-extensions; [
      # Microsoft
      ms-vscode-remote.remote-ssh
      ms-vscode-remote.remote-ssh-edit
      ms-azuretools.vscode-docker

      # vim
      vscodevim.vim
      vspacecode.whichkey

      # Languages
      golang.go
      ms-python.python
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

    # Rest of your VS Code configuration remains the same
    userSettings = {
    };

    keybindings = [
    ];
  };
}