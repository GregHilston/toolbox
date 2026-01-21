# NixOS Configuration Assistant

## Available Hosts
- **foundation** (x86_64 WSL VM)
- **isengard** (x86_64 ThinkPad T420)
- **mines** (aarch64 VM on M4 Mac via VMware Fusion)
- **home-lab** (x86_64 VM)

## Common Mistakes to Avoid

1. **Module imports**: Always use relative paths in module imports (e.g., `../../modules/home` not absolute paths)
2. **Testing before deploy**: NEVER skip `just ft <host>` before `just fr <host>`
3. **Hardware configs**: Never edit `hardware-configuration.nix` files - they're auto-generated
4. **Flake updates**: After updating flake.lock, always test build before deploying
5. **Architecture mismatch**: Check host architecture (x86_64-linux vs aarch64-linux) matches the config
6. **Home Manager**: User packages go in `modules/home/default.nix`, not system packages
7. **WSL specifics**: foundation host needs `wsl.enable = true` and related WSL config

## Verification Workflow

ALWAYS test before deploying:
1. Format: `nix fmt .`
2. Test build: `just ft <host>`
3. Deploy: `just fr <host>`

## Quick Commands

- Test: `/test-config <host>`
- Deploy: `/deploy-config <host>`
- Full verification: `/verify <host>`
- Commit: `/commit <message>` (add `--push` to push, `--pr` to create PR)

## File Locations

- User packages: [modules/home/default.nix](modules/home/default.nix)
- GUI apps: [modules/programs/gui/](modules/programs/gui/)
- TUI apps: [modules/programs/tui/](modules/programs/tui/)
- System packages: [modules/common/default.nix](modules/common/default.nix)
- Host configs: `hosts/<type>/<hostname>/default.nix`

## Testing

Use `/verify <host>` before committing. Test builds catch 90% of issues.

## Dev Container Validation

A Docker dev container is available for validating configs without a NixOS host:

```bash
# Build image (one-time, from nixos/.devcontainer/)
docker build -t nixos-devcontainer .

# Validate all configs
docker run --rm -v /path/to/nixos:/workspaces/nixos nixos-devcontainer just validate
```

**What it can do:** `nix flake check`, dry-run builds, catch config errors
**What it cannot do:** `nixos-rebuild switch`, test services, hardware-specific behavior

See [.devcontainer/README.md](.devcontainer/README.md) for details.

If needed, see [README.md](README.md) for detailed documentation on repository structure, VM setup, and development workflows.
