# VS Code Configuration
#
# This module serves two purposes:
# 1. Manages VS Code installation and extensions on bare metal hosts (foundation, isengard)
# 2. Acts as reference documentation for extension list on VM hosts (mines, vm-x86, vm-arm)
#
# For VM hosts running on macOS:
# - VS Code runs on the macOS host with extensions managed there
# - Connects to NixOS VM via Remote-SSH extension
# - This extension list serves as reference for what to install
# - nix-ld (enabled in common/default.nix) allows VS Code Server to run
#
# For bare metal hosts:
# - VS Code is fully managed by NixOS using this configuration
# - Extensions are declaratively installed from this list
#
{pkgs, ...}: {
  programs.vscode = {
    enable = true;
    package = pkgs.vscode-fhs;
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
            version = "1.322.0";
            sha256 = "sha256-PekZQeRqpCSSVQe+AA0XLAwC3K0LGtRMbfnN7MxfmGA=";
          }
          {
            name = "roo-cline";
            publisher = "RooVeterinaryInc";
            version = "3.17.1";
            sha256 = "sha256-gfzn0KulOHUKcG3LNF7+g7VwkDHR4BYsmq730Uuv2ZU=";
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
