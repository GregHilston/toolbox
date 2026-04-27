# NixOS Configuration Assistant

## Available Hosts
- **foundation** (x86_64 WSL VM)
- **isengard** (x86_64 ThinkPad T420)
- **mines** (aarch64 VM on M4 Mac via VMware Fusion)
- **home-lab** (x86_64 VM)
- **dungeon** (aarch64-darwin MacBook Pro 16" M3 Pro — nix-darwin)

## Common Mistakes to Avoid

1. **Module imports**: Always use relative paths in module imports (e.g., `../../modules/home` not absolute paths)
2. **Testing before deploy**: NEVER skip `just ft <host>` before `just fr <host>`
3. **Hardware configs**: Never edit `hardware-configuration.nix` files - they're auto-generated
4. **Flake updates**: After updating flake.lock, always test build before deploying
5. **Architecture mismatch**: Check host architecture (x86_64-linux vs aarch64-linux vs aarch64-darwin) matches the config
6. **Home Manager**: User packages go in `modules/home/default.nix`, not system packages
7. **WSL specifics**: foundation host needs `wsl.enable = true` and related WSL config
8. **No hardcoded IPs**: Never put IP addresses directly in host configs or modules. All host IPs are defined in `config/vars.nix` under `networking.hosts`. Reference them as `vars.networking.hosts.<name>.lan` or `vars.networking.hosts.<name>.tailscale`. If a new host or IP is needed, add it to `vars.nix` first.
9. **SSH config**: SSH client matchBlocks are managed centrally in `modules/programs/tui/ssh.nix` using vars. Do not add SSH host entries in individual host configs.

## Verification Workflow

ALWAYS test before deploying:

Be sure to select the host, and only the host we're working with. IE if we're developing on the mines host, do not attempt to run `$ just ft home-lab` or `$ just fr home-lab`:

### NixOS hosts
1. Format: `nix fmt .`
2. Test build: `just ft <host>`
3. Deploy: `just fr <host>`

### Darwin hosts (dungeon)
1. Format: `nix fmt .`
2. Test build: `just dt <host>`
3. Deploy: `just dr <host>`

## Quick Commands

- Test: `/test-config <host>`
- Deploy: `/deploy-config <host>`
- Full verification: `/verify <host>`
- Commit: `/commit <message>` (add `--push` to push, `--pr` to create PR)

## LLM Setup (oMLX)

Local LLM inference is configured via **oMLX** (MLX GUI wrapper with prefix caching). The entire setup is reproducible and version-controlled.

**Configuration files:**
- **Settings**: `~/Git/toolbox/dot/omlx/.omlx/settings.json` — server config, model dirs, sampling params, caching
- **Models**: `~/Git/toolbox/dot/omlx/.omlx/models/` — downloaded models (gitignored, stored locally)
- **Tool integration**: `hosts/macs/moria/qwen-code.nix` — points qwen-code to local oMLX on localhost:8000

**Current setup:**
- **moria** (M4 Max 128GB): Runs oMLX server, hosts models (Qwen3.6 27B 8bit, Gemma 4 26B, GPT-OSS 120B)
- **dungeon** (M3 Pro 36GB): Can point tools to moria's oMLX server via network aliases in settings.json

**Why oMLX?**
- Prefix caching: Repeated prompts (like roger's system prompt) reuse cached representations (~1.55x faster TTFT on cache hits)
- Full JSON config: Reproducible, declarative, git-tracked
- Fastest single-token on Apple Silicon (faster than Ollama, comparable to MLX)
- OpenAI-compatible API for tool integration

**To add LLM support to dungeon:**
Create `hosts/macs/dungeon/llm-tools.nix` (mirror of moria's qwen-code.nix) pointing to `moria.local:8000` or use Tailscale alias from settings.json.

**Reference:** See `~/Git/notes/ref-llm-inference-tools.md` for broader LLM tool decision guide.

## File Locations

- User packages: [modules/home/default.nix](modules/home/default.nix)
  - Python packages: Use `python3.withPackages (ps: with ps; [package-name])`
- GUI apps: [modules/programs/gui/](modules/programs/gui/)
- TUI apps: [modules/programs/tui/](modules/programs/tui/)
- System packages: [modules/common/default.nix](modules/common/default.nix)
- Darwin system config: [modules/darwin/common.nix](modules/darwin/common.nix)
- Darwin Homebrew casks: [modules/darwin/homebrew.nix](modules/darwin/homebrew.nix)
- Darwin home-manager: [modules/darwin/home.nix](modules/darwin/home.nix)
- Host IPs / networking vars: [config/vars.nix](config/vars.nix) (`networking.hosts`)
- SSH client config: [modules/programs/tui/ssh.nix](modules/programs/tui/ssh.nix)
- Host configs: `hosts/<type>/<hostname>/default.nix`
- LLM settings: `~/Git/toolbox/dot/omlx/.omlx/settings.json` (reproducible oMLX config)

## Testing

Use `/verify <host>` before committing. Test builds catch 90% of issues.

## Updating Pinned App Versions (e.g. Open WebUI Desktop)

Some apps are fetched directly from GitHub releases rather than nixpkgs (e.g. Open WebUI desktop in [modules/darwin/home.nix](modules/darwin/home.nix) and [modules/home/default.nix](modules/home/default.nix)). To upgrade them:

1. Update `version` in the derivation to the new release tag.
2. Update the `url` if the filename changed (check the GitHub releases page).
3. Set `sha256 = lib.fakeSha256;` — this is a known-bad placeholder.
4. Try to build: `just dt <darwin-host>` or `just ft <linux-host>`.
5. Nix will fail with: `hash mismatch... got: sha256-REALHASH`.
6. Replace `lib.fakeSha256` with that printed hash and rebuild — it should succeed.

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
