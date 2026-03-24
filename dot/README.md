# Dot

A directory containing all my configuration files, managed with [GNU Stow](https://www.gnu.org/software/stow/).

## How It Works

Each subdirectory is a **stow package**. The directory structure inside each package mirrors where files should land relative to `~`. For example:

```
dot/aerospace/.aerospace.toml  -->  ~/.aerospace.toml
```

## Usage

From the `dot/` directory:

```bash
just list              # List all available packages
just stow aerospace    # Stow a single package
just unstow aerospace  # Unstow a single package
just restow aerospace  # Restow (unstow + stow) a single package
just stow-all          # Stow all packages
just unstow-all        # Unstow all packages
just restow-all        # Restow all packages
just dry-run aerospace # Preview what stow would do
just build-i3-gaps     # Build i3-gaps config for current host, then stow
```

> **Note:** Stow won't overwrite existing regular files. If a target file already exists (not as a symlink), remove it first, then stow.

## Packages

```
├── aerospace/          # AeroSpace tiling window manager (macOS)
├── i3-gaps-pkg/        # i3-gaps config (built from per-host fragments, then stowed)
├── i3-pkg/             # i3 config
├── redshift/           # Redshift color temperature (Linux)
├── skhd/               # skhd hotkey daemon (macOS)
├── tmux/               # tmux terminal multiplexer
├── vim-pkg/            # vim/neovim config (.vimrc + .vim/)
├── yabai/              # yabai tiling window manager (macOS)
└── zsh/                # zsh config (.zshrc + .p10k.zsh)
```

## Generating a Brewfile

Homebrew packages are managed declaratively via nix-darwin (`nixos/modules/darwin/homebrew.nix`). If you need a standalone Brewfile (e.g. for a work laptop without nix-darwin):

```bash
brew bundle dump --file=~/Brewfile
```

This captures everything currently installed by Homebrew into a portable Brewfile.
