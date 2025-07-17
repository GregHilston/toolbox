{pkgs, ...}: {
  programs.vscode = {
    enable = true;
    package = pkgs.vscode;
    mutableExtensionsDir = false;

    profiles.default = {
      enableExtensionUpdateCheck = false;
      enableUpdateCheck = false;
      extensions = with pkgs.vscode-extensions;
        [
          # Microsoft
          ms-vscode-remote.remote-ssh
          ms-vscode-remote.remote-ssh-edit
          ms-azuretools.vscode-docker

          # tools
          vscodevim.vim
          vspacecode.whichkey
          rooveterinaryinc.roo-cline

          # languages
          golang.go
          jnoortheen.nix-ide
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
        ]
        ++ pkgs.vscode-utils.extensionsFromVscodeMarketplace [
          {
            name = "copilot";
            publisher = "GitHub";
            version = "1.270.1373";
            sha256 = "sha256-5HlZKJQBdzXBjWki5owYD9vMo72A/6ukoDNgzIIaJt8=";
          }
        ];

      userSettings = {
        "vim.handleKeys" = {
          "<C-p>" = false;
          "<C-f>" = false;
          "<C-n>" = false;
          "<C-b>" = false;
        };
      };

      keybindings = [
        # Add keybindings here as needed
      ];
    };
  };
}
