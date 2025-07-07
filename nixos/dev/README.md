# Development Environment with Nix Flakes

A multi-language development environment using Nix flakes as a replacement for
Ansible provisioning. Includes shared tooling and language-specific shells for
Go, TypeScript, and Ruby development.

| Environment | Command                    | Additional Tools                    | Use Case                                |
| ----------- | -------------------------- | ----------------------------------- | --------------------------------------- |
| Default     | `nix develop`              | Base toolset only                   | General development, dotfile management |
| Go          | `nix develop .#golang`     | `go`, `gopls`, `gotools`, `gofumpt` | Go development with language server     |
| TypeScript  | `nix develop .#typescript` | `nodejs`, `yarn`, `typescript`      | TypeScript/JavaScript development       |
| Ruby        | `nix develop .#ruby`       | `ruby`, `bundler`                   | Ruby development                        |

## Prerequisites

- [Nix](https://nixos.org/download.html) with flakes enabled

- Docker daemon running (for Docker tools)

**Docker Note**: The Docker tools require the Docker daemon to be running
system-wide. On NixOS, add `virtualisation.docker.enable = true` to your
`configuration.nix`.

## Quick Start

````bash
nix develop              # Default environment
nix develop .#golang     # Go development
nix develop .#typescript # TypeScript development## How to Use

## DevShells

- **Default environment**:

**Tools available**: `zsh`, `git`, `stow`, `docker`, `flatpak`, `curl`, `wget`,
`direnv`, `nix-direnv`, `nixfmt`:

Activate with:

```bash
nix develop
````

- **Golang Environment**:

**Tools available**: `go`, `gopls`, `gotools`, `gofumpt`

Activate with:

```bash
nix develop .#golang
```

- **Typescript Environment**:

**Tools available**: `nodejs`, `yarn`, `typescript`

Activate with:

```bash
nix develop .#typescript
```

- **Ruby Environment**:

**Tools available**: `ruby`, `bundler`

Activate with:

```bash
nix develop .#ruby
```

**Notes**:

- All devshells include the base toolset (`zsh`, `git`, `stow`, `docker`, etc.)
  as `commonTools` in the `flake.nix`.

- Each language-specific shell adds the relevant compilers, language servers,
  and package managers.

- You can further customize each shellHook or add more tools as needed.

## Direnv and Nix-Direnv

`direnv` will automatically activate the default devShell when you `cd` into the
`dev` directory **after** you type `direnv allow` to activate it. If you don't
like this auto activation, delete the `.envrc` in the `dev` directory.

With multiple devShells in the same flake I'm not sure how much benifit you'll
get from it but you can edit the `.envrc` to change which shell is automatically
activated if you so choose:

> Note: you can only choose one at a time with direnv.

```zsh
use flake   # Default
# OR
# use flake .#golang
# OR
# use flake .#typescript
# OR
# use flake .#ruby
```

If the default devShell automatically activates and you want to use say the
golang devShell, you can type `nix develop .#golang` to manually activate it or
any other.

# GNU Stow

How to Use Stow in This Project

1. Copy or clone your dotfiles directory into the dev/dotfiles directory:

```bash
cp -r ~/my-dotfiles dev/dotfiles
# or
git clone https://github.com/yourname/dotfiles.git dev/dotfiles
```

2. Enter the development environment:

```bash
nix develop
```

3. Symlink your dotfiles into your home directory:

```bash
# Manual approach
cd dotfiles
stow -t $HOME *
```

- This command tells Stow to create symlinks for all packages (subdirectories)
  in `dotfiles/` into your home directory.

- For example, `dotfiles/zsh/.zshrc` will be symlinked as `~/.zshrc`, and
  `dotfiles/nvim/.config/nvim/init.vim` as `~/.config/nvim/init.vim`

4. Result: Your home directory now has symlinks pointing to the files in your
   dotfiles directory. Any changes you make to the files in dotfiles/ are
   immediately reflected in your environment.

What the Provided Script Does

```bash
if [ -d "$PWD/dotfiles" ]; then
  stow -d "$PWD/dotfiles" -t "$HOME" *
fi
```

- Checks if a dotfiles directory exists in your current working directory.

- If it does, runs Stow to symlink all subdirectories (packages) from dotfiles/
  into your home directory.

- This automates the setup, so you only need to copy your dotfiles and run the
  command once.

**Best Practices**

- Keep each tool’s config in its own subdirectory (e.g., `zsh/`, `git/`,
  `nvim/`).

- Version-control your dotfiles directory with Git for easy backup and sharing.

- Use Stow’s `-t` option to specify the target directory (usually your home
  directory).

### Troubleshooting

- **"Oh My Zsh can't be loaded from bash"**: The environment automatically
  switches to zsh

- **Docker commands fail**: Ensure Docker daemon is running

- **Stow conflicts**: Remove existing dotfiles or use `stow --adopt`
