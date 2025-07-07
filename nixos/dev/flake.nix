{
  description = "DevShell replacing Ansible provisioning, with multi-language support";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
    ...
  }:
    flake-utils.lib.eachDefaultSystem (
      system: let
        pkgs = import nixpkgs {inherit system;};
        # Shared tools for all environments
        commonTools = [
          pkgs.zsh
          pkgs.git
          pkgs.stow
          pkgs.docker-compose
          # pkgs.docker   # Optional - docker-compose includes basic docker commands
          pkgs.flatpak
          pkgs.curl
          pkgs.wget
          pkgs.direnv
          pkgs.nix-direnv
          pkgs.nixfmt-rfc-style
          pkgs.oh-my-zsh # Add Oh My Zsh here
          # Example plugins (add more as needed)
          pkgs.zsh-autosuggestions
          pkgs.zsh-syntax-highlighting
        ];
      in {
        devShells = {
          # Default devshell with general tools
          default = pkgs.mkShell {
            packages = commonTools;
            shellHook = ''
              export SHELL=$(which zsh)
              if [ ! -d "$HOME/.oh-my-zsh" ]; then
                echo "Installing Oh My Zsh..."
                sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
              else
                echo "Oh My Zsh is already installed."
              fi
              if ! docker info >/dev/null 2>&1; then
                echo "⚠️  Docker daemon not running (required for docker-compose)"
              fi
              if [ -d "$PWD/dotfiles" ]; then
                echo "Applying dotfiles with stow..."
                stow -d "$PWD/dotfiles" -t "$HOME" * || echo "Warning: stow failed"
              fi
              echo " ⚒️ Welcome to your Nix dev environment! ⚒️"
              echo "🛠️ Tools available: zsh, git, stow, docker, flatpak, curl, wget, direnv, nix-direnv, nixfmt 🛠️"
              if [ -z "$DIRENV_IN_ENVRC" ]; then
                exec zsh
              fi
            '';
          };

          # Golang devshell
          golang = pkgs.mkShell {
            packages =
              commonTools
              ++ [
                pkgs.go
                pkgs.gopls
                pkgs.gotools
                pkgs.gofumpt
              ];
            shellHook = ''
              echo "🐹 Golang dev environment ready! 🐹"
              echo "🛠️ Tools available: go, gopls, gotools, gofumpt 🛠️"
            '';
          };

          # Ruby devshell
          ruby = pkgs.mkShell {
            packages =
              commonTools
              ++ [
                pkgs.ruby
                pkgs.bundler
              ];
            shellHook = ''
              echo "💎 Ruby dev environment ready! 💎"
              echo "🛠️ Tools available: ruby, bundler 🛠️"
            '';
          };

          # TypeScript devshell
          typescript = pkgs.mkShell {
            packages =
              commonTools
              ++ [
                pkgs.nodejs
                pkgs.yarn
                pkgs.typescript
              ];
            shellHook = ''
              echo "🟦 TypeScript dev environment ready! 🟦"
              echo "🛠️ Tools available: nodejs, yarn, typescript 🛠️"
            '';
          };
        };
      }
    );
}
