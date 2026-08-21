# NixOS Configuration Assistant

## Self-Testing Changes

Always verify your own changes before asking the user to test. Detect the current host with `hostname` and dry-run build against it:

- **Darwin hosts**: `nix build .#darwinConfigurations.$(hostname).system --dry-run`
- **NixOS hosts**: `nix build .#nixosConfigurations.$(hostname).config.system.build.toplevel --dry-run`

These commands do NOT require `sudo` and catch most evaluation and dependency errors. Run this after every config change so the user doesn't have to be your test runner.

## Available Hosts

`just list-hosts`. Three are Darwin (**moria** M4 Max/oMLX server, **dungeon** M3 Pro
headless Docker server, **citadel** M5 Pro work laptop) and take `just dt`/`dr`;
the rest are NixOS and take `just ft`/`fr`. **mines** is a NixOS guest on moria — not
a Darwin host. **rohan** is a console-only writerdeck that skips the workstation layer.

## Home-manager profiles: three layers, pick the lowest one that fits

`modules/home/` is a stack, not a grab bag. Add things to the **narrowest** layer
that needs them:

| Layer | File | Who imports it | What belongs there |
| --- | --- | --- | --- |
| identity | `modules/home/common.nix` | every host, transitively | username, home dir, stateVersion, `programs.home-manager.enable` — nothing else |
| workstation | `modules/home/workstation.nix` | NixOS + Darwin | the shared CLI/dev baseline: `modules/programs/tui`, `basePackages.homePackages`, nh, yazi, searxngr stow |
| platform | `modules/home/default.nix` (NixOS)<br>`modules/darwin/home.nix` (macOS) | one platform each | only what is genuinely platform-specific (NixOS: `claude-code` + the GUI block; macOS: fonts, mflux, open-webui-desktop, pi/opencode) |

rohan deliberately stops at the identity layer and cherry-picks TUI modules by
hand — the workstation baseline (ollama, go, duckdb, ffmpeg…) has no business on a
writerdeck.

Home-manager *wiring* (`useGlobalPkgs`, `useUserPackages`, `backupFileExtension`,
`extraSpecialArgs`) is set once for both module systems by `homeManagerModule` in
`flake-modules/hosts.nix` — the option paths are identical under NixOS and
nix-darwin. Never repeat it in a host.

## Shell integration lives in ONE place

`modules/programs/tui/zsh/` owns every shell hook, alias, wrapper function, and
exported variable, written into `~/.zshrc.local`. The per-tool modules
(`eza`, `fzf`, `zoxide`, `atuin`, `direnv`, `zellij`, `yazi`) install the binary
and render genuine config files only.

This is because we do **not** use home-manager's `programs.zsh` — we stow a
portable `.zshrc`. So `enableZshIntegration`, `shellWrapperName`, and friends have
nothing to hook into and silently do nothing. If you set one, it will look correct
and have no effect; put the line in the zsh module instead.

## Desktop (GUI) vs headless NixOS hosts

The KDE Plasma desktop is **opt-in**, via one option the host sets on itself:

```nix
custom.desktop.enable = true;   # in hosts/<type>/<host>/default.nix
```

That option is defined in `modules/common/desktop.nix` and drives both the system
desktop stack (xserver/sddm/plasma6/pipewire/1Password GUI) and the GUI home packages
in `modules/home/default.nix`, which reads it back with
`osConfig.custom.desktop.enable`. One switch, so the two halves can't disagree.

- **GUI host** (isengard, mines): sets `custom.desktop.enable = true`.
- **Headless host** (foundation, home-lab): sets nothing — no desktop, no GUI
  packages, no per-service `mkForce` overrides needed.

rohan (the writerdeck) is console-only and doesn't import `modules/common`, so it
doesn't have the option at all. To add a new GUI host, set the option in its host
file; a new headless host needs nothing.

> Historical note: this used to be a second flag, `vars.enableGui`, threaded through
> `hostVars` in `flake-modules/hosts.nix` purely to supply `custom.desktop.enable`'s
> default. Hosts now set the real option directly.

## Where apps live: brew on macOS, nix on NixOS

No dilemma — nixpkgs can't package many macOS `.app`s (and nix-darwin drives brew
declaratively), while Homebrew/Linuxbrew is not idiomatic on NixOS. So the same app is
declared in two places by platform, with truly-shared CLI tools hoisted into
`config/base-packages.nix`:

- **macOS (Darwin):** `modules/darwin/homebrew-base.nix` (every Mac) + per-host casks.
- **NixOS CLI:** `modules/common/default.nix` systemPackages extras — the "Darwin gets
  it via Homebrew" list (`just`, `stow`, `gh`, `pandoc`, `ngrok`, …).
- **NixOS GUI:** the `enableGui` block in `modules/home/default.nix` (a local binding
  reading `osConfig.custom.desktop.enable`), or a managed `programs.*` module under
  `modules/programs/gui/` — currently `firefox`, `ghostty`, `vscode`, which get stylix
  theming for free. GUI apps reach every `enableGui` NixOS host (mines + isengard), so add
  there rather than per-host unless you want just one.

**aarch64 caveat:** mines is aarch64-linux. Several proprietary GUI apps (slack, spotify,
discord, bitwarden-desktop) are **x86_64-linux only** in nixpkgs — hence the
`system != "aarch64-linux"` gate in `modules/home/default.nix`. Check
`nix eval .#nixosConfigurations.<host>.pkgs.<pkg>.meta.platforms` before adding a GUI app
for an ARM host.

## Launching GUI apps at login: a launchd `open -a` agent

Menu-bar apps have to already be running to do anything, and they fail *silently* when
they aren't — no Handy means Caps Lock still behaves and nothing dictates; no Ice means
the stock cluttered menu bar. So each gets a launchd user agent: `modules/darwin/handy.nix`
(imported per-host by citadel and moria; headless dungeon has the cask but no use for a
dictation app) and `modules/darwin/ice.nix` (imported from `modules/darwin/common.nix`, so
all three Macs). The Linux equivalent is a home-manager `systemd.user.services.*` unit
bound to `graphical-session.target` — see handy in `modules/home/default.nix`.

The shape is always the same, and *why* is the part worth remembering:

- **`/usr/bin/open -g -j -a /Applications/Foo.app`, not the bundle's inner binary.** macOS
  TCC keys Microphone/Accessibility/Screen-Recording grants on a LaunchServices launch, so
  `open` is what a double-click does and the grants from `docs/darwin-post-deploy.md`
  survive. It's also idempotent — `open -a` on a running app just activates it, so the
  agent bootstrap on every `just dr <host>` can't leave two copies running. `-g` = don't
  steal focus, `-j` = launch hidden.
- **`RunAtLoad` only, never `KeepAlive`.** `open` exits as soon as LaunchServices takes
  over, so KeepAlive reads that as a crash and respawns forever. The tradeoff: a real
  crash isn't restarted. Fine — the missing menu-bar icon is the tell.
- **Not the app's own "Launch at login" toggle.** Those register an `SMAppService` login
  item in app-written state (e.g. Handy's `settings_store.json`) that nix neither owns nor
  can assert. Keep the in-app toggle **off** so the two don't double-register.
- **Log to `~/Library/Logs/<app>.log`.** On a fresh host the agent can load before Homebrew
  installs the cask; `Unable to find application named ...` shows up there rather than
  failing the rebuild.

## PI WEB is the exception to the launchd rule above

Every other long-running user service here gets a nix-declared
`launchd.user.agents.*`. **PI WEB does not, on purpose.**

`pi-web install` generates `~/Library/LaunchAgents/com.pi-web.{web,sessiond}.plist`
from its own plan and **replaces** them every time it runs — which is also the
documented upgrade path. `pi-web doctor` then re-reads what is installed and
compares it back: `shellCommand` and `workingDirectory` must match the plan, and
the two agents must agree with each other. So a nix-written plist is not merely
redundant. It either loses to the next `pi-web install`, or it fails doctor — and
doctor is the tool you reach for when PI WEB misbehaves.

So the split is: **nix owns the config, PI WEB owns the services.**

- `modules/darwin/pi-web.nix` symlinks `dot/pi-web/.config/pi-web/config.json`
  into `~/.config/pi-web` and stops there. A symlink, not a `home.file`, because
  PI WEB's Settings UI writes back to that file and `/nix/store` is read-only.
- `just pi-web-setup` runs `npm install -g` + `pi-web install` once per host.
  It is idempotent (pi-web *replaces* its services) so it doubles as the upgrade
  path, and it is in `docs/darwin-post-deploy.md` so `just checklist` surfaces it.

It is not in activation for the ordinary reasons this file already gives:
activation is root, has no user login session for `launchctl bootstrap`, and
should not do network work.

**Nothing in this setup needs a key in that plist**, which is lucky, because the
next `pi-web install` would regenerate it away. Note also that `~/.zshrc.local`
— the nix-generated shell file — does not reach a PI WEB session: its agents run
`/usr/bin/env zsh -lc <cmd>`, a *login* but **non-interactive** shell, so
`~/.zshenv` and `~/.zprofile` are sourced and `~/.zshrc` is skipped, and
`~/.zshrc.local` is sourced by `~/.zshrc`. Anything a pi extension must read
from `process.env` under PI WEB has to come from a file it reads itself, not
from a shell rc.

## Common Mistakes to Avoid

1. **Module imports**: Always use relative paths in module imports (e.g., `../../modules/home` not absolute paths)
2. **Testing before deploy**: NEVER skip `just ft <host>` before `just fr <host>`
3. **Hardware configs**: Never edit `hardware-configuration.nix` files - they're auto-generated
4. **Flake updates**: After updating flake.lock, always test build before deploying — a
   *real* build, not `--dry-run`. See "Flake lock bumps" below.
5. **Architecture mismatch**: Check host architecture (x86_64-linux vs aarch64-linux vs aarch64-darwin) matches the config
6. **Home Manager**: User packages go in `modules/home/default.nix`, not system packages
7. **WSL specifics**: foundation host needs `wsl.enable = true` and related WSL config
8. **No hardcoded IPs**: Never put IP addresses directly in host configs or modules. All host IPs are defined in `config/vars.nix` under `networking.hosts`. Reference them as `vars.networking.hosts.<name>.lan` or `vars.networking.hosts.<name>.tailscale`. If a new host or IP is needed, add it to `vars.nix` first.
9. **SSH config**: SSH client match blocks are managed centrally in `modules/programs/tui/ssh.nix` using vars. Do not add SSH host entries in individual host configs.
10. **`vars.user.name` is the LOCAL account, never a remote login**: it is
    `greghilston` on citadel (work) and `ghilston` everywhere else. The account to
    log in as *on a remote machine* is that machine's own fact and lives beside its
    addresses as `vars.networking.hosts.<name>.user`. Using `vars.user.name` for an
    ssh `User` silently breaks on citadel.

## Flake lock bumps — evaluation is not a build

Every check here — `just validate`, CI, `nix build --dry-run`, the Self-Testing
commands above — stops at instantiating a derivation. That answers "does this
configuration make sense?", never "does it build?". A fixed-output hash is invisible
to evaluation by definition: whether the fetched bytes match is a build-time fact.
This is not theoretical — a 2026-08-16 nixpkgs bump passed every dry-run and then
failed on a re-rolled tarball hash in a `jetbrains-mono` dependency.

**So: before deploying a lock bump, build one host for real.**

```bash
nix build --no-link .#darwinConfigurations.<host>.system      # macOS
nix build --no-link .#nixosConfigurations.<host>.config.system.build.toplevel
```

Do it on the machine you are about to `just dr`/`just fr`, since a cached path on one
host proves nothing about another architecture.

For the **weekly bot bump** this is now automated: `update-flake-lock.yml`'s
`build-darwin` job really builds `darwinConfigurations.dungeon.system` on a macOS
runner and comments the verdict on the PR, so a green tick there does mean "it builds".
It is macOS on purpose — nixpkgs' aarch64-darwin outputs are cached far less reliably
than x86_64-linux, so a Linux runner substitutes the cached result and sees nothing.
~6.6 GB of closure, mostly substituted: affordable weekly, not per-PR.

That covers dungeon only. **For any lock change you make by hand, or before deploying
to moria or citadel, still build it yourself** — nothing checks those.

When a bump does turn out to be broken, check whether the fix has already landed
upstream before working around it:

```bash
gh api "repos/NixOS/nixpkgs/commits?path=<path/to/package.nix>&per_page=5" \
  --jq '.[] | "\(.commit.committer.date)  \(.sha[0:9])  \(.commit.message | split("\n")[0])"'
gh api "repos/NixOS/nixpkgs/compare/<fix-sha>...nixos-unstable" --jq '.behind_by'
```

`behind_by == 0` means the channel has it and a re-run of `nix flake update` is all that
is needed. Anything else means waiting is cheaper than patching — the channel usually
catches up within days, and the weekly bot PR will pick it up on its own.

## VMware Fusion VM (mines) — Access & Networking

`mines` is a **NixOS aarch64-linux** guest under VMware Fusion on the Mac host `moria`.
It is **not** a Darwin host — rebuild it with `just ft mines` / `just fr mines`
(`nh os …`). Running `just dt/dr mines` fails with `darwin-rebuild: command not found`
inside the guest; `dt`/`dr` are for the Macs only.

**Reaching it from moria:** SSH over the VMware NAT subnet (`192.168.180.0/24`). The
host reaches the guest on this subnet even when the guest has no *internet*, so SSH
works for remote repair.

The guest IP is **pinned via a VMware NAT DHCP reservation** so it no longer drifts.
On the host, `/Library/Preferences/VMware Fusion/vmnet8/dhcpd.conf` maps the VM's MAC to
a fixed address **outside** the dynamic `range` (`.128–.254`), added *below* the
`DO NOT MODIFY SECTION`:

```
host mines {
    hardware ethernet 00:0c:29:89:17:27;   # `ip link show enp10s0` in the guest
    fixed-address 192.168.180.10;          # matches vars.networking.hosts.mines.lan
}
```

Editing that file needs `sudo` (real terminal). After editing, restart networking
(`sudo "/Applications/VMware Fusion.app/Contents/Library/vmnet-cli" --stop && … --start`)
and renew the guest lease (`sudo systemctl restart NetworkManager` in the VM). If the
lease ever drifts again (e.g. before the reservation existed), find the current one with:

```
awk '/^lease /{ip=$2} /starts/{s=$0} /hardware/{h=$0} /^}/{print ip"  "s"  "h}' \
  /var/db/vmware/vmnet-dhcpd-vmnet8.leases | grep -i mines   # newest timestamp wins
```

**"No internet" is usually broken DNS, not routing.** Symptom triage on the guest:
`ping 1.1.1.1` works but `ping github.com` says *"Name or service not known"*, and
`host github.com` resolves while `git`/`curl`/`ping`/`nix` fail with *"server returned
answer with no data"*. Root cause: **VMware's NAT DNS proxy (`192.168.180.2`) cannot
handle EDNS0**, and NixOS puts `options edns0` in `resolv.conf` by default. `host`/`dig`
resolve because they don't go through glibc — they mislead you into thinking DNS is fine.
Isolate it by editing `/etc/resolv.conf` (a writable file, unlike the read-only
`/etc/resolvconf.conf` symlink) to the NAT nameserver **without** `options edns0` — it
resolves instantly. Restarting host VMware networking
(`sudo "/Applications/VMware Fusion.app/Contents/Library/vmnet-cli" --stop && … --start`,
needs a real terminal — `sudo` can't prompt under a non-interactive `!` run) does **not**
help. The durable, root-cause fix (committed in `hosts/vms/mines/default.nix`) is one line:

```nix
networking.resolvconf.dnsExtensionMechanism = false;  # drop `options edns0`
```

Note: `networking.nameservers` is silently ignored under NetworkManager + openresolv, so
forcing public resolvers that way does not work; disabling EDNS0 keeps the NAT DNS and is
the smaller fix.

### mines OOM-kills the foreground scope (no swap on a tight RAM cap)

Symptom: a tmux/Claude-Code scope is killed by the kernel ("system is low on memory")
during a memory spike — nix eval/build, Claude Code plus spawned subagents, and the Plasma
desktop all at once. Root cause: the guest ships with **no swap** (`free -h` → `Swap: 0B`),
so any transient overshoot of the VM's RAM cap goes straight to the OOM killer with zero
reclaimable headroom. Fix (committed in `hosts/vms/mines/default.nix`): `zramSwap.enable`
(compressed RAM-backed swap, no disk I/O, sized at `memoryPercent = 50`). Complementary
host-side lever: raise the guest's RAM in VMware Fusion — moria has 128GB and the guest
currently sees ~31GiB. Do the Fusion RAM bump *first* (a rebuild itself spikes memory),
then deploy. Avoid fanning out many Claude Code subagents inside this RAM-limited guest.

## Home-manager activation fails on a long-dormant host (stale `.backup` pileup)

`backupFileExtension = "backup"` makes home-manager move any file it wants to own to
`<file>.backup`. Stale ones used to collide and abort activation with *"Existing file
X.backup would be clobbered"*.

**Fixed** in `flake-modules/hosts.nix`: `overwriteBackup = true` clobbers a stale
backup with a warning instead of aborting, on every host. If a pileup still appears on
a long-dormant host, archive it non-destructively:

```bash
mkdir -p ~/.hm-stale-backups-$(date +%Y%m%d)
find ~ -maxdepth 3 -name '*.backup' -exec mv {} ~/.hm-stale-backups-.../ \;
```

## Deploying to NixOS from the toolbox repo — gotchas

- **Stow runs under a stripped PATH.** `programs/tui/zsh` stows the portable dotfiles
  (`~/.zshrc`, `~/.tmux.conf`, …) from `dot/` in a home-manager activation. Home-manager
  activation runs with a **minimal PATH that excludes `/run/current-system/sw/bin`**, so a
  bare `stow` (or any system tool) silently no-ops on NixOS — the classic symptom is a
  *bare shell prompt* (no powerlevel10k) because `~/.zshrc` was never linked. Always call
  such tools by absolute nix path (`${pkgs.stow}/bin/stow`), never rely on PATH in an
  activation script.
- **The same stripped PATH silently disabled pi's package install.**
  `modules/programs/tui/pi.nix` guards its activation on `command -v pi`, and pi
  lives at `/opt/homebrew/bin/pi` on Darwin — not on activation's minimal PATH.
  The guard failed, the whole block was skipped, and nothing said so: activation
  prints `Activating installPiPackages` and simply never prints its success line.
  It went unnoticed for as long as it existed, because pi installs missing
  packages from `settings.json` at startup anyway — it only surfaced when two
  *new* packages failed to appear after a deploy. If an activation block guards
  on `command -v`, give it an explicit PATH first.
- **Claude Code on NixOS comes from nixpkgs `claude-code`**, added to
  `modules/home/default.nix` — *not* the `curl|bash` native installer in `tui/claude.nix`
  (that installer assumes `~/.local/bin` is on PATH, which it isn't on the VM, so it
  silently no-ops). Darwin keeps the native self-updating installer; the installer's
  `! command -v claude` guard makes it defer to the nix-installed binary on NixOS.

## Verification Workflow

ALWAYS test before deploying:

Be sure to select the host, and only the host we're working with. IE if we're developing on the mines host, do not attempt to run `$ just ft home-lab` or `$ just fr home-lab`:

### NixOS hosts
1. Format: `nix fmt .`
2. Test build: `just ft <host>`
3. Deploy: `just fr <host>`

### Darwin hosts (dungeon, moria, citadel)
1. Format: `nix fmt .`
2. Test build: `just dt <host>`
3. Deploy: `just dr <host>`

## Quick Commands

- Test: `/test-config <host>`
- Deploy: `/deploy-config <host>`
- Full verification: `/verify <host>`

`/commit` is the **global** command from `claude-commands/commit.md`. This directory
deliberately does not define its own — a project command of the same name shadows the
global one, and the copy that used to live here was both weaker and hardcoded to a Linux
path, so it broke on all three Macs.

## LLM Setup (oMLX)

Local LLM inference is configured via **oMLX** (MLX GUI wrapper with prefix caching). The entire setup is reproducible and version-controlled.

**Configuration files:**
- **Settings**: `~/Git/toolbox/dot/omlx/.omlx/settings.json` — server config, model dirs, sampling params, caching
- **Models**: `~/Git/toolbox/dot/omlx/.omlx/models/` — downloaded models (gitignored, stored locally)
**Topology — the two oMLX servers are independent; neither is a client of the other:**
- **moria** (M4 Max 128GB): runs oMLX **only for moria itself** (consumed at `localhost:8000`).
  Hosts the big models (Qwen3.6 27B 8bit, Gemma 4 26B, GPT-OSS 120B) for local use.
- **dungeon** (M3 Pro 36GB): runs oMLX as the **shared inference server for low-power remote
  clients**. The Windows NixOS-WSL2 (foundation) and the Pixel 8 (Termux) reach it on
  LAN/Tailscale `:8000` — e.g. via `~/Git/notes/sync.sh`, which uses `localhost` on moria but
  falls back to dungeon everywhere else. rohan also points at dungeon (inline `models.json`).

**Why oMLX?**
- Prefix caching: Repeated prompts (like roger's system prompt) reuse cached representations (~1.55x faster TTFT on cache hits)
- Full JSON config: Reproducible, declarative, git-tracked
- Fastest single-token on Apple Silicon (faster than Ollama, comparable to MLX)
- OpenAI-compatible API for tool integration

**Adding model variants:**
For extended-context or other model profiles, see `dot/omlx/CLAUDE.md` → "Creating Model Variants". The nix activation script is in `modules/darwin/omlx.nix` and handles symlink creation on all Darwin hosts automatically.

**Reference:** See `~/Git/notes/ref-llm-inference-tools.md` for broader LLM tool decision guide.

## File Locations

`ls modules/` and `ls hosts/*/`. The layering is in "Home-manager profiles" above;
platform split in "Where apps live".

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

## ⚠️ Never put `docker-desktop` in `homebrew-base.nix`

**citadel only.** OrbStack owns `/usr/local/bin/docker` on dungeon and moria, and
Docker Desktop was never running there — installing it hijacks that path, after which
the Docker CLI works only by borrowing OrbStack's socket.

Dangerous specifically because `cleanup = "none"` with `upgrade = true` lets a stray
cask drift in silently rather than failing. The guardrail is repeated inline at both
edit sites (`homebrew-server.nix`, `hosts/macs/citadel/default.nix`).

```bash
brew list --cask --versions | grep -iE "docker-desktop|orbstack"   # what is actually installed
ls -l /usr/local/bin/docker
```

Read the machine, not the nix config: `cleanup = "none"` is exactly the case where a
stray cask sits on disk while the declared cask list looks clean.

## `just dr` re-prompts for a password at every cask — don't chase the sudo ticket

Homebrew runs `sudo --reset-timestamp` unconditionally at the top of every invocation,
with no env opt-out, so **nothing ticket-based survives `brew bundle`** — not a longer
`timestamp_timeout`, not `timestamp_type=global`, not a `sudo -v` keep-alive. All three
were tried. A sudoers rule is the only lever, and it works because the prompt is a
plain tty prompt, not a GUI Authorization dialog.

**Fixed** in `modules/darwin/common.nix`: NOPASSWD for only the binaries brew
escalates, plus `security.pam.services.sudo_local.reattach = true` so Touch ID works
from tmux. Not a security boundary — a speed bump.

A syntax error in `/etc/sudoers.d/` locks you out of sudo entirely, so verify before
deploying, and check each granted path exists (sudoers matches the resolved path):

```bash
nix eval --raw '.#darwinConfigurations.<host>.config.environment.etc."sudoers.d/10-nix-darwin-extra-config".text' > /tmp/su
visudo -c -f /tmp/su
```

## Darwin `postActivation` is ONE shared bash script — always use a subshell

`system.activationScripts.postActivation.text` is `types.lines`: nix-darwin concatenates
every module's fragment into a **single** bash script. Three consequences that have already
bitten this repo:

1. **`set -e`/`-u`/`pipefail` leak forward.** A bare `set -euo pipefail` at the top of one
   fragment silently applies to every fragment ordered after it — including
   **home-manager's own activation**, which is not written to run under those options.
2. **`exit 1` kills the whole script, not your fragment.** dungeon's GitHub-SSH guard used
   to `exit 1` at line 86 of the concatenated script, while home-manager activation started
   at line 89 — so a missing SSH key aborted activation before any dotfiles, `.zshrc.local`,
   or user packages were linked.
3. **Ordering is by `mkBefore`/`mkAfter`**, not file order (see `modules/darwin/omlx.nix`).

So: wrap any fragment that wants strict mode in a subshell, and make failure non-fatal.

```nix
system.activationScripts.postActivation.text = ''
  (
    set -euo pipefail
    ...
  ) || echo "WARNING: <host> post-activation block failed; continuing."
'';
```

Inspect the real concatenated script before trusting a change:

```bash
nix eval --raw '.#darwinConfigurations.<host>.config.system.activationScripts.postActivation.text' > /tmp/pa.sh
bash -n /tmp/pa.sh   # syntax check
```

**Don't do network or repo work in activation.** It runs as root, so it needs a
`sudo -H -u "$USER"` trampoline and has no access to the user's ssh-agent. Use a launchd
*user* agent instead — see `launchd.user.agents.home-lab-sync` in `hosts/macs/dungeon` and
`bin/home-lab-sync.sh`.

## Git hooks do not run in a `git worktree` — silently

`nix develop` installs the hooks in `flake-modules/dev.nix` (treefmt on commit,
`nix flake check` on push). **They do not fire in a worktree**, and nothing says so:
the commit simply succeeds with no hook output at all. Not "the hook failed" — the
hook was never found.

Cause is upstream, in git-hooks.nix's installation script:

```bash
common_dir=$(git rev-parse --path-format=absolute --git-common-dir)
common_dir=${common_dir#$GIT_WC/}                    # deliberately made relative
git config --local core.hooksPath "$common_dir/hooks"
```

It goes out of its way to make the path **relative** (`.git/hooks`), and
`core.hooksPath` is `--local`, which worktrees *share*. In a worktree `.git` is a
file, not a directory, so `.git/hooks` resolves to nothing.

`git config --local --unset core.hooksPath` fixes it — git then falls back to
`$GIT_COMMON_DIR/hooks`, which resolves correctly from both — but it does not stick,
because the next `nix develop` writes it straight back.

To actually run a hook from a worktree, override it for the one command:

```bash
git -c core.hooksPath="$(git rev-parse --path-format=absolute --git-common-dir)/hooks" push
```

So: **do not treat a clean commit in a worktree as evidence it passes the hooks.**
Verify from the main checkout, or with the override above.

## Dev Container Validation

See [.devcontainer/README.md](.devcontainer/README.md). It can `nix flake check` and
dry-run builds; it cannot `nixos-rebuild switch` or test hardware behaviour.

## Automatic Nix Garbage Collection for Darwin Hosts — PROPOSED, NOT IMPLEMENTED

Darwin runs Determinate Nix (`nix.enable = false`), so nix-darwin's `nix.gc` module
asserts out. **There is no scheduled GC on any Mac** — reclaim by hand with
`just delete-all-old-generations`. Adopting Determinate's own collector is the
intended fix — see <https://docs.determinate.systems/guides/nix-darwin/>. The
step-by-step adoption plan was removed from here rather than relocated; it is
recoverable from git history if wanted.

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

**Note:** headless dungeon does *not* require the VNC dance — a 1Password service
account token at `~/.config/op/service-account-token` (mode 600) is the preferred
path and `just secrets` picks it up automatically (`nixos/justfile`). VNC is the
fallback when no token exists. See the root `CLAUDE.md` → Secret Management.

**Decision: defer.** 1Password stays the source of truth. The manual headless `just secrets`
step is tolerable while dungeon is the only headless Darwin host. **Revisit (lean agenix)**
if a second headless host appears, or if the VNC-unlock dance becomes a recurring pain —
both decrypt at activation to tmpfs and eliminate the plaintext-on-disk + GUI-unlock steps.
