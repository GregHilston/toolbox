# NixOS Configuration Assistant

## Self-Testing Changes

Always verify your own changes before asking the user to test. Detect the current host with `hostname` and dry-run build against it:

- **Darwin hosts**: `nix build .#darwinConfigurations.$(hostname).system --dry-run`
- **NixOS hosts**: `nix build .#nixosConfigurations.$(hostname).config.system.build.toplevel --dry-run`

These commands do NOT require `sudo` and catch most evaluation and dependency errors. Run this after every config change so the user doesn't have to be your test runner.

## macOS caps the GPU at 75% of RAM, and oMLX does not know

`iogpu.wired_limit_mb` defaults to `0`, which is **not** unlimited — it means
"the built-in default", and that is **75% of unified memory**. On moria's 128 GB
that is 96 GB. Measured 2026-09-22 with Qwen3.6-35B (19 GB) and gpt-oss-120b
(59 GB) both resident: a steady **86-87 GB**, into which the KV cache then grows.

oMLX budgets against its own `max_model_memory: auto`, which resolves to ~84%
(107.5 GB), **above** what the kernel will wire. So its LRU plans against
memory it cannot have, and the wall it actually hits is invisible to it.

`modules/darwin/gpu-wired-limit.nix` raises the kernel limit above oMLX's
ceiling so oMLX's own manager is the only limiter. It computes
`total - reserveGb` at boot from `hw.memsize`, never goes below the 75% the
kernel would have chosen, and no-ops under `minTotalGb`.

**`/etc/sysctl.conf` is ignored on modern macOS.** It has to be a root launchd
daemon with `RunAtLoad`, which is also why the value resets on every reboot.
macOS 13 spelled the key `debug.iogpu.wired_limit`; 14+ uses
`iogpu.wired_limit_mb`. The daemon tries both.

To check the live value: `sysctl iogpu.wired_limit_mb` (`0` = the 75% default),
and `curl -s localhost:8000/health` for what oMLX thinks its ceiling is.

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
they aren't — no FluidVoice means Caps Lock still behaves and nothing dictates. So each gets a
launchd user agent:

- `modules/darwin/fluidvoice.nix` — per-host (citadel, moria); see "FluidVoice" below.
- `modules/darwin/vorssaint.nix` — every Mac, via `common.nix`, for the same reason. Plain
  `open -a`; its *other* job, seeding Vorssaint's Features hub (the app
  has no config file, only a UserDefaults domain), deliberately does **not** live in the
  agent. Activation order is agents → Homebrew → postActivation, so an agent-hosted seed
  runs before the cask exists and then has to race whoever opens the app first — a race it
  lost on moria's first deploy, permanently, because the app's wizard sets the same
  "already set up" marker the seed is gated on. Its header has the full reasoning.

The Linux equivalent is a home-manager `systemd.user.services.*` unit bound to
`graphical-session.target` — see handy in `modules/home/default.nix` (Linux still dictates
with Handy).

The shape is always the same, and *why* is the part worth remembering:

- **`/usr/bin/open -g -j -a /Applications/Foo.app`, not the bundle's inner binary.** macOS
  TCC keys Microphone/Accessibility/Screen-Recording grants on a LaunchServices launch, so
  `open` is what a double-click does and the grants from `docs/darwin-post-deploy.md`
  survive. It's also idempotent — `open -a` on a running app just activates it, so the
  agent bootstrap on every `just dr <host>` can't leave two copies running. `-g` = don't
  steal focus, `-j` = launch hidden. (FluidVoice wraps this in a script and drops `-j`;
  see below.)
- **`RunAtLoad` only, never `KeepAlive`.** `open` exits as soon as LaunchServices takes
  over, so KeepAlive reads that as a crash and respawns forever. The tradeoff: a real
  crash isn't restarted. Fine — the missing menu-bar icon is the tell.
  > Worth knowing when you are tempted to put real work in one of these: nix-darwin
  > reloads a user agent only when its generated plist *differs* from the installed
  > one, so on an unchanged config the agent is never re-bootstrapped and `RunAtLoad`
  > never fires again. A `just dr` does **not** re-run these scripts. That is fine for
  > `open -a`, which the next login handles, and it is one of the reasons `vorssaint.nix`
  > does its preference seeding from `postActivation` instead.
- **Not the app's own "Launch at login" toggle.** Those register an `SMAppService` login
  item in app-written state (e.g. Handy's `settings_store.json`) that nix neither owns nor
  can assert. Keep the in-app toggle **off** so the two don't double-register.
- **Log to `~/Library/Logs/<app>.log`.** On a fresh host the agent can load before Homebrew
  installs the cask; `Unable to find application named ...` shows up there rather than
  failing the rebuild.

## FluidVoice — dictation and voice commands on citadel and moria

`modules/darwin/fluidvoice.nix`, enabled with `services.fluidvoice.enable`. Karabiner
turns Caps Lock into F18 (dictate), Shift+Caps Lock into F19 (Command Mode, an LLM agent
that runs shell commands, asking first) and Option+Caps Lock into F20 (Write Mode). The
seeded activation mode is "automatic", and it covers all three keys: a tap toggles
hands-free recording, a hold is push-to-talk. A hands-free Command or Write capture ends on
the same chord; a plain Caps Lock tap switches it to dictation instead. Escape cancels.
Handy stays installed but no longer starts at login or owns F18; Linux hosts keep Handy.

What it does, all from `postActivation` as the user (the Vorssaint shape, same reasons).
The logic is `modules/darwin/fluidvoice-activate.sh`, a plain bash file; `fluidvoice.nix`
only passes it values in the environment, so `tests/test_fluidvoice_activate.py` runs the
real script against a scratch defaults domain with `pgrep`/`osascript`/`pkill` stubbed.

- **Seeds hotkeys once**, gated on `PrimaryDictationShortcuts` being absent in the
  `com.FluidApp.app` domain, so a hotkey changed in the app is never overwritten. Shortcuts
  are JSON stored as plist data (`Models/HotkeyShortcut.swift` upstream). To re-seed: quit
  FluidVoice, `defaults delete com.FluidApp.app PrimaryDictationShortcuts`, `just dr <host>`
  (re-seeding also reopens onboarding; click through it).
- **Writes `OnboardingCompleted = false`.** Any pre-set hotkey counts as "used before" and
  the app would skip onboarding, which is where permissions and the model download happen.
- **Binds both `fn+F18` and bare F18.** macOS sets the fn flag on some F-key events (why
  Handy stored `fn+f18`) and FluidVoice matches modifiers exactly. Command and Write Mode take
  a single shortcut, so each gets the form measured on moria: `fn+F19`, but bare F20 — F20
  arrives without fn. Rebind in the app if one never fires; a listen-only `CGEventTap`
  printing `keyboardEventKeycode` and `flags` shows what a chord really sends.
- **Takes F18 and launch-at-login from Handy** by editing its `settings_store.json`,
  quitting Handy first because it writes the store back on quit. Handy applies
  `autostart_enabled` on its own next launch, so its login item unregisters itself then.
- **Launches silently at login, unless onboarding is unfinished.** FluidVoice reveals and
  focuses its window on any launch it does not see as a login item, `-g` notwithstanding.
  The agent's script passes `--env FLUID_SIMULATE_LOGIN_LAUNCH=1` and the seed sets
  `ShowMainWindowAtLoginLaunch = false` and `ShowInDock = false`. Onboarding only renders in
  that window, so while `OnboardingCompleted` is not `1` the script launches loudly instead;
  otherwise a `just dr` over SSH would leave a Mac with no mic grant and no visible app.
  Upstream calls the env var a testing hook. The cask is `auto_updates`, so it could vanish in
  a Sparkle update rather than a `brew upgrade`; the cost is a window at login.
  **Never `-j`**: it launches the app *hidden*, and a hidden app's windows include the
  recording overlay. Hotkeys and dictation still worked, but the overlay never appeared
  (moria, 2026-10-04: the log said `bottom_show_start`, the screen showed nothing).
- **Every write quits a running FluidVoice first**, because the app holds its settings in
  memory and writes them back. `quit_app` asks with a 10 s AppleEvent timeout, then sends
  SIGTERM. A plain `quit app` waited out AppleScript's default 120 s on a FluidVoice wedged
  after a Command Mode run (hotkeys arrived, recording never started) and the deploy applied
  nothing. If it survives even SIGTERM, only the step that needed the quit is skipped, with a
  warning; Handy, `fluidvoice-ax` and the relaunch still run.
- **Turns AI streaming off** (`EnableAIStreaming`, no UI toggle in v1.6.9). FluidVoice's
  streaming chat-completions parser keeps only `toolCalls.first` and concatenates every
  call's arguments regardless of `index`, so when Qwen makes two tool calls at once
  Command Mode fails with "Invalid response from LLM". The non-streaming parser reads them
  all and Command Mode runs one per step. Still unfixed upstream as of 2026-10-03; Write
  Mode and Command Mode replies now arrive whole instead of word by word.
- **Owns the model routing, on every deploy** (in-app edits to these revert). Only when a
  value drifts does it quit FluidVoice, write, and relaunch. Values come from the 1.6.9
  source and its binary, and were confirmed live on moria, 2026-10-04:
  - Dictation on Fluid-1: `SelectedProviderID = fluid-1` plus `SelectedDictationPromptID =
    __FLUID_1__`, the shipped id the startup normaliser keeps (the public source's
    `__PRIVATE_AI_PROVIDER__` is deleted on launch). The post-processing gate refuses Fluid-1
    as a per-prompt provider, so the default prompt's own provider/model is blanked: it
    otherwise outranks the global one. Measured 2026-10-03: 0.06 s warm against 0.6 s for
    Qwen3.6 `:lab`, the same 88% usable over 69 cases, no stall behind a long pi prefill
    (worst 1.1 s against 85 s); Qwen did better only on corrections (36/36 against 30/36).
  - Write and Command Mode unsynced (Fluid-1 refuses both) on an oMLX provider with the fixed
    id `omlx`. Write Mode gets `:lab`: 0.42 s per rewrite against 10.6 s with thinking on, 44/45
    usable graded blind; Qwen3.5-2B was 0.20 s but 12/45.
  - The provider is "verified" by writing `VerifiedProviderFingerprints["custom:omlx"] =
    sha256("<baseURL>|<key>")`, the app's own check. The key comes from
    `~/.omlx/settings.json` and goes into `SavedProviders[].apiKey`; the app moves it into its
    Keychain item itself at launch (`scrubSavedProviderAPIKeys`), so nothing touches the
    Keychain and no access prompt appears.
  - **Waits for onboarding.** Onboarding writes the provider keys itself, so while
    `OnboardingCompleted` is not `1` the step only says so: a fresh Mac gets its routing on
    the first deploy *after* onboarding.
  - **Writes nothing unless every value computed.** The providers, prompt configs and
    fingerprint are built before the app is quit; if `jq` cannot parse what is stored, the
    step is skipped rather than writing an empty value over it.
  - Compares providers sorted by id, so one added in the app is kept and causes no drift.
  - **Lists the models in `AvailableModelsByProvider["custom:omlx"]`.** 1.6.9's Command Mode reads its model list only from there, never from `SavedProviders`, and a custom provider has no built-in defaults, so without it Command Mode fails with "Command Mode needs a selected chat model" while Write Mode works (citadel, 2026-10-05). Upstream main falls back to the saved provider; drop this once a release ships that. Written as a union and checked as a subset, so the app's own model refresh is kept and causes no drift.
  - If the app cannot store the key (a locked Keychain), it leaves it in `SavedProviders`,
    and every deploy sees drift and quits the app again. `defaults read com.FluidApp.app
    SavedProviders` showing a non-empty `apiKey` after a launch is the tell.
  - The model is `services.omlxDeploy.lightModel.dir`, so a new light model reaches
    FluidVoice too (its `:lab` profile must exist for it in `model_profiles.json`).
- **Adds Custom Dictionary entries** on every activation, add-only by replacement, for
  jargon both models mangle ("quinn" → Qwen, "o mlx" → oMLX). Plain regex on the
  transcript, before any model.
- **Handy is best-effort and runs after the seed**, so a corrupt Handy store or a Handy that
  won't quit prints a warning and never blocks FluidVoice.

What stays manual: permissions, and downloading Parakeet and Fluid-1, both from the app
(`docs/darwin-post-deploy.md`).

### Write Mode in Electron apps: `fluidvoice-ax`

**Symptom.** Select text in Slack, Obsidian or VS Code, say "make this more formal", and
FluidVoice *types* "Please provide the text you would like me to make more formal." at the
cursor instead of replacing the selection. `~/Library/Logs/Fluid/Fluid.log` says:

```
[TextSelectionService] Frontmost app fallback could not resolve focused element
[TextSelectionService] Selection capture failed: no selected text found
[ContentView] Rewrite mode triggered, text captured: false
```

**Why.** FluidVoice 1.6.9 gets the selection one way only: the Accessibility API, reading
`kAXSelectedTextAttribute` off the focused element (`Services/TextSelectionService.swift`).
There is no clipboard fallback (upstream #220) and the bug is open upstream (#259, where
Obsidian fails and TextEdit works). Native Cocoa apps always answer. **Electron apps do not**:
Chromium builds its accessibility tree only once an assistive tool asks for it, and on macOS
the ask is setting the attribute `AXManualAccessibility = true` on the app's AXApplication
element — Electron's documented switch for third-party assistive tech. VoiceOver flips it
for itself; FluidVoice never does. With no tree, there is no focused element, so Write Mode
gets no text and the model, correctly, asks for some.

**What.** `modules/darwin/fluidvoice-ax.swift`, ~60 lines: it sets `AXManualAccessibility`
on every app in `services.fluidvoice.accessibleApps` (default Slack, Obsidian, VS Code) when
it starts, and again whenever one launches or comes to the front. Re-setting is a no-op, and
doing it on activation covers an app that was not ready at launch. It logs only changes, to
`~/Library/Logs/fluidvoice-ax.log`, one line per app pid with the AX result code: `0` worked,
`-25211` means it lacks the Accessibility permission.

**How it is built and run**, and why each piece:

- **Compiled during activation with `/usr/bin/swiftc`** into
  `~/Library/Application Support/fluidvoice-ax/fluidvoice-ax`, only when the source's store
  path changes (recorded beside it in `source`). Outside the store so the entry in the
  Accessibility list keeps one path across rebuilds. **The grant itself does not survive an
  edit**: the binary is ad-hoc signed, so macOS ties the grant to its hash, and a rebuilt
  binary can show as allowed in System Settings while every set returns `-25211`. After
  editing the Swift source, remove `fluidvoice-ax` from the Accessibility list with "−", let
  it prompt again (or add it with "+"), and check the log. A stable grant would need signing
  with a real certificate; not worth it for a file that rarely changes. Needs the Command
  Line Tools; without them activation warns and skips, rather than letting the `swiftc` shim
  pop an install dialog.
- **A `KeepAlive` launchd agent**, `org.nixos.fluidvoice-ax`, unlike the `open -a` agents
  above, because this is a real long-running process rather than a launcher. On a first deploy
  the agent loads before activation builds the binary; `ThrottleInterval = 30` keeps launchd's
  retries quiet until it exists, and activation `kickstart -k`s it after each build.
- **The Accessibility prompt** comes from the binary itself
  (`AXIsProcessTrustedWithOptions` with the prompt option), which also adds it to the list in
  System Settings → Privacy & Security → Accessibility.

**Costs.** An Electron app with its accessibility tree on uses somewhat more CPU and memory,
the same as it would under VoiceOver. VS Code additionally needs
`"editor.accessibilitySupport": "on"` in its settings (not managed here on macOS) so Monaco
mirrors the selection into the hidden text area the tree exposes; with Vim mode on, the
reply is pasted after the selection rather than over it, since Vim owns the keystroke.

**Debugging.** `tail -f ~/Library/Logs/fluidvoice-ax.log` shows what it set;
`launchctl print gui/$(id -u)/org.nixos.fluidvoice-ax` shows whether it runs. If an app still
fails, bring it to the front once (that re-applies) and check Fluid.log for
`text captured: true`.

**Measured on moria, 2026-10-04:** with the attribute set, Slack, Obsidian and VS Code all
logged `text captured: true` and Write Mode rewrote the selection; without it, all three
failed as above.

### Write Mode in Firefox: a Firefox policy, not `fluidvoice-ax`

**Symptom.** The same "Please provide the text…" in Firefox. Probing Firefox's AXApplication
element shows why: its focused element is the bare `AXWindow`, with nothing inside, until
something turns Firefox's accessibility service on.

**Why `fluidvoice-ax` cannot do it.** Firefox is not Electron: `AXManualAccessibility`
returns `-25205` (attribute unsupported); the string appears nowhere in Gecko. Gecko decides
in `accessible/mac/Platform.mm`:

```cpp
bool ShouldA11yBeEnabled() {
  EPlatformDisabledState disabledState = PlatformDisabledState();
  return (disabledState == ePlatformIsForceEnabled) ||
         ((disabledState == ePlatformIsEnabled) && sA11yShouldBeEnabled);
}
```

`sA11yShouldBeEnabled` is set only when an assistive tool sets **`AXEnhancedUserInterface`**
on the app (VoiceOver's way), or reads `AXRole` on the app element, which Gecko answers by
setting that same flag on itself (for Voice Control). It does not latch: every AX call
re-checks, so clearing the flag hides the tree again. **That flag is the problem.** AppKit
sees it too, and window managers that move windows through the Accessibility API (AeroSpace
here) get animated, sluggish moves for any app that has it. Tested and rejected for that
reason.

**What we use instead.** `ePlatformIsForceEnabled` comes from the pref
**`accessibility.force_disabled = -1`** (`accessible/base/nsAccessibilityService.cpp`), which
turns the service on with `AXEnhancedUserInterface` left at 0. It is a supported setup:
Mozilla's own macOS accessibility tests run with exactly this pref
(`accessible/tests/browser/mac/browser.toml`). The name reads backwards; `-1` means
"force enabled", `0` "on demand", `1` "force disabled".

**How it is applied.** As a Firefox enterprise policy in the **user** defaults domain, from
`fluidvoice.nix`:

```nix
system.defaults.CustomUserPreferences."org.mozilla.firefox" = {
  EnterprisePoliciesEnabled = true;
  Preferences."accessibility.force_disabled" = { Value = -1; Status = "default"; };
};
```

Firefox's macOS policy reader (`xpcom/base/nsMacPreferencesReader.mm`) reads
`[NSUserDefaults standardUserDefaults]` for `org.mozilla.firefox`, which includes
`~/Library/Preferences`, once `EnterprisePoliciesEnabled` is true; `Preferences` may set any
`accessibility.*` pref. Why this route and not the others:

- **Not `user.js` in the profile**: the profile folder's name is random per Mac, and macOS
  privacy protection denied a terminal even `ls` of `~/Library/Application Support/Firefox`.
- **Not `policies.json` in `Firefox.app/Contents/Resources/distribution/`**: a Firefox update
  replaces the app bundle and the file with it. (macOS Firefox does not read
  `/Library/Application Support/Mozilla/policies`.)
- `Status = "default"` sets the default only, so `about:config` can still change it;
  `"locked"` would forbid that.

**Costs and gotchas.**
- Firefox reads policies at startup only: **quit and reopen Firefox once** after the first
  deploy. Check `about:policies` (Active → `Preferences`) and `about:config` for the pref.
- Any policy makes Firefox say "Your browser is being managed by your organization" at the
  top of Settings. That is this policy, nothing else.
- **A managed Mac can override it.** If an MDM profile already pushes `org.mozilla.firefox`
  (look in `/Library/Managed Preferences`), its `Preferences` key replaces ours whole and the
  pref never applies. Check `about:policies` on citadel after the first deploy.
- The accessibility service then runs all the time, as under VoiceOver: some memory, and
  slower pages under heavy DOM churn.
- The value must be a real integer. `defaults write … '{ Value = -1; }'` stores the string
  `"-1"`, which does not work; nix-darwin writes `<integer>`.
- **The domain carries two policies.** This one, and `ExtensionSettings` from
  `modules/darwin/homebrew-base.nix`, which force-installs Obsidian Web Clipper on every
  Mac. nix-darwin merges them, so both share one `EnterprisePoliciesEnabled`.
- Removing the nix lines does **not** remove the keys (`CustomUserPreferences` never
  deletes). Undo only the policy you dropped: `defaults delete org.mozilla.firefox
  Preferences` for this one, `… ExtensionSettings` for the clipper. Leave
  `EnterprisePoliciesEnabled` while the other remains, or it stops applying too. Never
  delete the whole domain; Firefox keeps window state there.
- **Do not read `AXRole` on Firefox's app element** in anything we write: Gecko answers by
  setting `AXEnhancedUserInterface` on itself, policy or not. FluidVoice's own typing code
  can (its recursive search starts at the app element), but only on an Accessibility-insertion
  fallback that never ran here: it types by pasting.

**Tested 2026-10-04** on a throwaway Firefox launched through LaunchServices
(`open -n -g -a Firefox --args -no-remote -profile <tmp>`; launched as a child of a terminal
it cannot read its own profile folder and shows "Profile Missing") with only the policy in
place: the page's `<textarea>` was reachable as `AXTextArea`, its selected text read back,
and `AXEnhancedUserInterface` stayed 0. `about:policies` listed it as active.

### Making Write Mode work in another app ("foo")

Write Mode works in an app exactly when the app's focused element answers
`kAXSelectedTextAttribute`. Most apps fall into one of four kinds, and each kind has a known
fix. Steps:

1. **Try it and read the log.** Select text in foo, use Write Mode, then
   `grep -E 'Captured recording app context|text captured' ~/Library/Logs/Fluid/Fluid.log | tail -2`.
   `text captured: true` means foo already works. The context line gives foo's bundle id
   (also `osascript -e 'id of app "Foo"'`).
2. **Find out what kind of app foo is.**
   `ls "/Applications/Foo.app/Contents/Frameworks" | grep -i -E 'electron|chromium|cef'`
   finds Electron (and Chromium-embedding) apps. A Gecko app (Firefox, Thunderbird,
   Zen) has `XUL.framework` there.
3. **Probe it** with a few lines of Swift (from a terminal that has Accessibility): with foo
   in front and text selected, read `AXFocusedUIElement` off
   `AXUIElementCreateApplication(pid)`, then that element's `AXRole` and `AXSelectedText`.
   Then set the candidate switch below and read again. The probes used to work all this out
   were throwaway; `fluidvoice-ax.swift` is the reference for the calls.
4. **Apply the fix for its kind:**

| Kind | Symptom | Fix | Effort |
|---|---|---|---|
| Native Cocoa (TextEdit, Notes, Mail) | already works | none | none |
| **Electron** (Slack, Obsidian, VS Code, Discord, Notion, Linear…) | focused element missing (`-25212`) | add its bundle id to `services.fluidvoice.accessibleApps` and deploy; `fluidvoice-ax` picks it up | one line |
| **Gecko** (Firefox, Thunderbird, Zen) | focused element is a bare `AXWindow` | a policy setting `accessibility.force_disabled = -1` in that app's own defaults domain, like the Firefox block in `fluidvoice.nix` (Thunderbird: `org.mozilla.thunderbird`) | a few lines; test `about:policies` |
| **Chrome and other Chromium browsers** (Chrome, Arc, Brave, Edge) | like Electron | try adding the bundle id to `accessibleApps` first: Chromium honours `AXManualAccessibility` too. If that fails, the browser's own flag `--force-renderer-accessibility` | one line, maybe more |
| Custom-drawn UI (terminals that draw their own text, games, some Java and Qt apps) | focused element exists but has no `AXSelectedText` | nothing outside the app can fix it; copy the text and use Write Mode with no selection, or wait for FluidVoice's clipboard fallback (upstream #220) | not fixable here |

5. **Never use `AXEnhancedUserInterface`** to turn an app's accessibility on, even though it
   works on most apps (it is what VoiceOver sets). Window managers, AeroSpace here, move and
   resize any app that has it sluggishly. Reading `AXRole` on an app's *application* element
   can make Gecko set it on itself, so a probe should read roles on focused elements only.
6. **Write it down**: add the app to the tables and notes here, and to the post-deploy list if
   it needs a manual step.

For Electron and Chromium apps, accessibility costs the app some CPU and memory while on, the
same as running it under VoiceOver.

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
  `modules/programs/tui/pi.nix` guards its activation on `command -v npm`, and npm
  lives in `/opt/homebrew/bin` on Darwin — not on activation's minimal PATH.
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
