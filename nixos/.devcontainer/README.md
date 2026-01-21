# NixOS Dev Container

A Docker-based development container for validating NixOS configurations without affecting your host system.

## Overview

This container provides an isolated Nix environment that can:
- Validate flake syntax and evaluate all NixOS configurations
- Build system closures (dry-run) to catch configuration errors
- Run the language-specific dev shells from `dev/flake.nix`

It **cannot**:
- Run `nixos-rebuild switch` (requires a real NixOS system)
- Test actual service startup (no systemd)
- Test hardware-specific behavior

## Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Builds on `nixos/nix:latest`, adds flakes support, just, and zsh |
| `devcontainer.json` | VS Code dev container configuration |

## Usage

### VS Code (Recommended)

1. Open the `nixos/` folder in VS Code
2. When prompted, click "Reopen in Container"
   - Or: Cmd+Shift+P → "Dev Containers: Reopen in Container"
3. Run commands in the integrated terminal:
   ```bash
   just validate          # Check all host configs
   nix flake check        # Validate flake
   nix develop ./dev#golang  # Enter Go dev shell
   ```

### Docker CLI

```bash
# Build the image (from nixos/.devcontainer/)
docker build -t nixos-devcontainer .

# Run validation (from repo root or wherever your nixos/ folder is)
docker run --rm -v /path/to/nixos:/workspaces/nixos nixos-devcontainer just validate

# Interactive shell
docker run --rm -it -v /path/to/nixos:/workspaces/nixos nixos-devcontainer sh

# Check a specific host
docker run --rm -v /path/to/nixos:/workspaces/nixos nixos-devcontainer \
  nix build .#nixosConfigurations.mines.config.system.build.toplevel --dry-run
```

### devcontainer CLI

If you have the [devcontainer CLI](https://github.com/devcontainers/cli) installed:

```bash
cd nixos
devcontainer up --workspace-folder .
devcontainer exec --workspace-folder . just validate
```

## Available Commands

| Command | Description |
|---------|-------------|
| `just validate` | Run `nix flake check` and dry-run build all hosts |
| `nix flake check` | Validate flake syntax and evaluate outputs |
| `nix build .#nixosConfigurations.<host>.config.system.build.toplevel --dry-run` | Build a specific host config |
| `nix eval .#nixosConfigurations.<host>.config.<option>` | Evaluate a specific config value |
| `nix develop ./dev#<lang>` | Enter a language dev shell (golang, typescript, ruby) |

## Troubleshooting

### First build is slow
The first build downloads the `nixos/nix` base image and installs just/zsh. Subsequent builds use cached layers.

### Git safe directory warning
The container automatically runs `git config --global --add safe.directory /workspaces/nixos` to avoid Git ownership warnings.

### Flake evaluation is slow
First evaluation downloads and caches all flake inputs. Subsequent runs are faster. The cache persists within the container session but not across container rebuilds.
