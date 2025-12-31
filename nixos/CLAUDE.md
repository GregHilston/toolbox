# CLAUDE.md - NixOS Configuration Assistant Guide

## Project Overview

This is a personal NixOS configuration repository by Greg Hilston (ghilston) that manages system configurations for multiple machines using Nix Flakes. The repository follows a modular architecture for maintaining NixOS configurations across different hosts including physical machines (PCs) and virtual machines (VMs).

It was inspired by Mitchell Hashimoto's usage of NixOS in a VM running on a Macbook Pro laptop. He did this because he got the battery life and quality of a Mac, but the flexibility of Linux.

For references to websites and GitHub repositories on using a NixOS VM for development, see the **NixOS VM Development** section in [README.md](README.md#nixos-vm-development).

## Repository Structure

- **flake.nix**: Main configuration entry point defining inputs and outputs
- **config/vars.nix**: Centralized configuration variables (user info, paths, system settings)
- **hosts/**: Machine-specific configurations divided into:
  - `pcs/`: Physical machine configurations (foundation, isengard)
  - `vms/`: Virtual machine configurations (vm-x86, vm-arm, mines)
- **modules/**: Reusable configuration modules organized by:
  - `common/`: Shared system configurations
  - `home/`: Home Manager user package configurations
  - `programs/`: Application-specific configurations (GUI and TUI)
  - `gaming/`: Gaming-related configurations
  - `stylix/`: Theme and styling configurations

## Available Hosts

- **foundation**: x86_64-linux WSL configuration
- **isengard**: x86_64-linux ThinkPad T420 with hardware-specific modules
- **vm-x86**: x86_64-linux virtual machine
- **vm-arm**: aarch64-linux virtual machine
- **mines**: aarch64-linux virtual machine configuration (runs on M4 Max MacBook Pro via VMware Fusion)
  - Host filesystem sharing: macOS filesystem accessible at `/host` (read-write)
  - x86_64 emulation: Can run x86_64 binaries on ARM via QEMU
  - Passwordless sudo: Enabled for VM development workflow
  - Firewall: Disabled for easier port access (safe in NAT VM)
  - VS Code Remote-SSH: Runs on macOS host, connects to VM

## Build and Deploy Commands

The project uses `just` (alternative to Make) for common operations:

### Primary Commands

- `just deploy <host>`: Deploy configuration to specified host
- `just upgrade <host>`: Upgrade and deploy configuration
- `just debug <host>`: Debug deployment with verbose output
- `just fr <host>`: Fast rebuild using nh tool
- `just ft <host>`: Test rebuild without switching
- `just fu <host>`: Update flake and rebuild

### Utility Commands

- `just list-hosts`: Show available host configurations
- `just list-generations`: Show past NixOS generations
- `just up`: Update all flake inputs
- `just clean`: Remove generations older than 7 days
- `just gc`: Garbage collect unused nix store entries

## Development Environment

- **Shell**: Pre-configured nix-shell environment available via `nix-shell`
- **User**: Greg Hilston (ghilston@Gregory.Hilston@gmail.com)
- **Default packages**: alacritty (terminal), vscode (editor) or nvim (editor), zsh (shell)
- **Location**: ~/Git/toolbox/nixos

## Key Features

- Modular configuration system preventing duplication
- Home Manager integration for user package management
- Stylix theming system with custom wallpaper
- Hardware-specific configurations (ThinkPad T420 support)
- WSL support for development environments
- Gaming module for Steam and related tools
- Custom Neovim configuration with LazyVim
- VS Code integration with nix-vscode-extensions
- Git configuration management
- direnv for automatic project environment loading

## Testing and Linting

- Use `nix fmt .` for formatting Nix files (uses alejandra formatter)
- Test configurations with `just ft <host>` before deploying
- Debug issues with `just debug <host>` for verbose output

## Common Workflows

1. **Making changes**: Edit relevant module files, test with `just ft <host>`, then deploy with `just fr <host>`
2. **Adding new packages**: Add to appropriate module in `modules/` directory
3. **New host setup**: Create new directory in `hosts/` with `default.nix` and `hardware-configuration.nix`
4. **Updates**: Run `just up` to update flake inputs, then `just fu <host>` to rebuild

## Mines VM Specific Features

### Host Filesystem Sharing
The entire macOS filesystem is accessible at `/host` with read-write access:
- Access Downloads: `ls /host/Users/$USER/Downloads`
- Edit macOS files: `nvim /host/Users/$USER/Documents/file.txt`
- Share projects: Work on files in `/host` and see changes immediately on macOS
- umask=22: New files created are readable by group/others, writable by owner only

### x86_64 Emulation
Run x86_64 binaries on ARM when needed:
- Automatic via QEMU user mode emulation
- Useful for npm packages or proprietary tools that only ship x86_64 binaries
- Some performance overhead, but generally transparent

### direnv Usage
Automatically load project environments:
1. Create `.envrc` file in project directory
2. Run `direnv allow` to trust the file
3. direnv automatically loads/unloads environment when entering/leaving directory
4. Works seamlessly with nix-shell and flake.nix

Example `.envrc` for Nix project:
```bash
use flake
```

### Development Workflow
- **No sudo password**: Run `sudo` commands without password prompt
- **No firewall**: All ports accessible for web app testing
- **VS Code Remote-SSH**: VS Code on macOS connects to VM seamlessly
- **Clipboard integration**: Copy/paste between VM and macOS works out of the box

## File Locations for Common Tasks

- User packages: modules/home/default.nix
- GUI applications: modules/programs/gui/
- Terminal applications: modules/programs/tui/
- System-wide packages: modules/common/default.nix
- Machine-specific config: hosts/<machine-type>/<hostname>/default.nix

## Recent Changes

- **Mines VM improvements** (based on mitchellh-nixos-config patterns):
  - Added host filesystem sharing at `/host` for macOS integration
  - Enabled x86_64 binary emulation on aarch64
  - Fixed boot console mode to eliminate boot errors
  - Disabled firewall for easier development (safe in NAT VM)
  - Enabled passwordless sudo for development workflow
  - Cleaned up commented virtio kernel modules
- Added direnv module for automatic project environment loading
- Added nh build tool for faster rebuilds
- Integrated yazi file explorer
- Updated justfile with flake_path parameter
- Commented out enhancer-for-youtube due to recognition issues
- Cleaned up empty common.nix files

This configuration emphasizes modularity, maintainability, and reproducibility across different hardware platforms and use cases.

## Reference Repositories

  Local clones of NixOS configuration references are available in `~/Git/nixos-references/`:
  - `mitchellh-nixos-config`: Mitchell Hashimoto's NixOS VM setup (primary inspiration)
  - `dustinlyons-nixos-config`: macOS-focused Nix config with excellent documentation
  - `fryuni-config-files`: Module and repository organization reference
  - `gaetanlepage-nix-config`: GUI/TUI program separation patterns
  - `hans-chrstn-dotfiles`: Per-program configuration examples
  - `alexnabokikh-nix-config`: Additional configuration patterns

  These can be searched for patterns, ideas, and implementation examples.
