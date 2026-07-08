# NixOS Configuration Assistant

## Self-Testing Changes

Always verify your own changes before asking the user to test. Detect the current host with `hostname` and dry-run build against it:

- **Darwin hosts**: `nix build .#darwinConfigurations.$(hostname).system --dry-run`
- **NixOS hosts**: `nix build .#nixosConfigurations.$(hostname).config.system.build.toplevel --dry-run`

These commands do NOT require `sudo` and catch most evaluation and dependency errors. Run this after every config change so the user doesn't have to be your test runner.

## Available Hosts
- **foundation** (x86_64 WSL VM)
- **isengard** (x86_64 ThinkPad T420)
- **mines** (aarch64 VM on M4 Mac via VMware Fusion)
- **home-lab** (x86_64 VM)
- **rohan** (x86_64 ThinkPad X201 Tablet — writerdeck, console-only)
- **dungeon** (aarch64-darwin MacBook Pro 16" M3 Pro — nix-darwin, headless Docker/oMLX-client server)
- **moria** (aarch64-darwin M4 Max — nix-darwin, runs the oMLX inference server)
- **citadel** (aarch64-darwin MacBook Pro 14" M5 Pro — nix-darwin, Mozilla work laptop)

## Desktop (GUI) vs headless NixOS hosts

The KDE Plasma desktop is **opt-in**. A single flag, `vars.enableGui`, drives both
the system desktop stack (`modules/common/desktop.nix`, gated on
`custom.desktop.enable = vars.enableGui or false`) and the GUI home packages in
`modules/home/default.nix`. It's set per host in `flake-modules/hosts.nix`:

- **GUI host** (isengard, mines): `hostVars = vars // { enableGui = true; };`
- **Headless host** (foundation, home-lab): `enableGui = false` (the default) — no
  desktop, no GUI packages, no per-service `mkForce` overrides needed.

rohan (the writerdeck) is console-only and doesn't import `modules/common`, so it's
unaffected by this flag. To add a new GUI host, set `enableGui = true` in its
`hostVars`; a new headless host needs nothing.

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
**Current setup:**
- **moria** (M4 Max 128GB): Runs oMLX server, hosts models (Qwen3.6 27B 8bit, Gemma 4 26B, GPT-OSS 120B)
- **dungeon** (M3 Pro 36GB): Can point tools to moria's oMLX server via network aliases in settings.json

**Why oMLX?**
- Prefix caching: Repeated prompts (like roger's system prompt) reuse cached representations (~1.55x faster TTFT on cache hits)
- Full JSON config: Reproducible, declarative, git-tracked
- Fastest single-token on Apple Silicon (faster than Ollama, comparable to MLX)
- OpenAI-compatible API for tool integration

**Adding model variants:**
For extended-context or other model profiles, see `dot/omlx/CLAUDE.md` → "Creating Model Variants". The nix activation script is in `modules/darwin/omlx.nix` and handles symlink creation on all Darwin hosts automatically.

**Reference:** See `~/Git/notes/ref-llm-inference-tools.md` for broader LLM tool decision guide.

## File Locations

- Shared package baseline (NixOS + Darwin, system + home): [config/base-packages.nix](config/base-packages.nix)
- User packages: [modules/home/default.nix](modules/home/default.nix) (NixOS-only extras + GUI)
  - Python packages: Use `python3.withPackages (ps: with ps; [package-name])`
- GUI apps: [modules/programs/gui/](modules/programs/gui/)
- TUI apps: [modules/programs/tui/](modules/programs/tui/)
- System packages (NixOS-only extras): [modules/common/default.nix](modules/common/default.nix)
- Cross-host NixOS baseline (nix settings, locale, user): [modules/common/core.nix](modules/common/core.nix)
- Desktop stack (opt-in, gated on `custom.desktop.enable`): [modules/common/desktop.nix](modules/common/desktop.nix)
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

Some apps are fetched directly from GitHub releases rather than nixpkgs (e.g. Open WebUI desktop in [modules/darwin/home.nix](modules/darwin/home.nix), Darwin only). To upgrade them:

1. Update `version` in the derivation to the new release tag.
2. Update the `url` if the filename changed (check the GitHub releases page).
3. Set `sha256 = lib.fakeSha256;` — this is a known-bad placeholder.
4. Try to build: `just dt <darwin-host>`.
5. Nix will fail with: `hash mismatch... got: sha256-REALHASH`.
6. Replace `lib.fakeSha256` with that printed hash and rebuild — it should succeed.

## `just dr` fails on Homebrew cleanup (`dir_s_rmdir ... .incomplete`)

If a Darwin rebuild dies at the `Homebrew bundle...` stage with something like:

```
==> Running `brew cleanup gh`...
Error: No such file or directory @ dir_s_rmdir - .../downloads/<hash>--foo.bottle.tar.gz.incomplete
Upgrading gh has failed!
`brew bundle` failed! 1 Brewfile dependency failed to install
```

the package upgrade itself **succeeded** — it's Homebrew's automatic post-upgrade cache
cleanup choking on a stale interrupted-download stub (`.incomplete`). `brew bundle`
propagates the non-zero exit, so `darwin-rebuild` (and `just dr`) fail even though nothing
is actually broken. **Fix:** `brew cleanup --prune=all` to purge the stale cache, then
re-run `just dr <host>`. (Durable option if it recurs: set `HOMEBREW_NO_INSTALL_CLEANUP=1`
so installs stop auto-cleaning — note this is unrelated to `homebrew.onActivation.cleanup`
in `modules/darwin/homebrew-base.nix`, which only controls Brewfile-drift uninstalls.)

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

## Automatic Nix Garbage Collection for Darwin Hosts

The darwin hosts run Determinate Nix (`nix.enable = false` in `modules/darwin/common.nix`),
so nix-darwin's built-in `nix.gc` module can't be used (it asserts `nix.gc.automatic` requires
`nix.enable`). **A hand-rolled `launchd.daemons.nix-gc` is no longer the right answer** —
Determinate Nix ships **Determinate Nixd**, a daemon that performs garbage collection natively.

To enable scheduled GC, adopt the Determinate nix-darwin module instead of writing custom
launchd jobs:

1. Add the flake input: `determinate.url = "github:DeterminateSystems/determinate"`.
2. Import `inputs.determinate.darwinModules.default` in `modules/darwin/common.nix`.
3. Configure the collector, e.g.:

```nix
{
  determinate-nix.customSettings = { };
  # GC strategy lives under the Determinate Nixd config:
  #   /etc/determinate/config.json (written by the module)
  # e.g. garbageCollector.strategy = "automatic";
}
```

See <https://docs.determinate.systems/guides/nix-darwin/> for the current option names
(`determinateNixd.garbageCollector.strategy`). This replaces — and is simpler than — the
old custom-daemon approach, and is correctly disk-pressure aware.

## Secret Management — Decision Record (1Password vs. agenix / sops-nix)

**Current approach (keep):** Secrets live in 1Password (vault **Infra**). Committed `.tpl`
files hold `{{ op://Infra/Item/field }}` references; `just secrets` runs `op inject` to
write the real (gitignored) files. See the toolbox root `CLAUDE.md` → "Secret Management"
for the exact commands and prerequisites.

**Why it's worth a note:** `op inject` writes **plaintext** generated files to disk and
needs an interactive 1Password GUI unlock. On headless **dungeon** that means connecting
via VNC + Touch ID before every `just secrets` — a manual, non-reproducible step that
doesn't fit the otherwise declarative activation flow.

**Alternatives considered (not adopted this round):**

- **agenix** — secrets are `age`-encrypted *into the repo* (safe to commit) and decrypted
  at activation to a tmpfs (RAM, never written to disk) using each host's existing SSH host
  key. Simplest fit for our small set of standalone tokens; no GUI, no manual step, works
  headless. Tradeoff: re-keying when host keys change, and editing requires the `agenix` CLI.
- **sops-nix** — same activation-time, key-based decryption but with `sops`/YAML/`age` and
  better ergonomics for *bundled* multi-key secret files. More machinery than we need today.

**Decision: defer.** 1Password stays the source of truth. The manual headless `just secrets`
step is tolerable while dungeon is the only headless Darwin host. **Revisit (lean agenix)**
if a second headless host appears, or if the VNC-unlock dance becomes a recurring pain —
both decrypt at activation to tmpfs and eliminate the plaintext-on-disk + GUI-unlock steps.
