# Darwin Post-Deploy Checklist

Run these tasks after initial deployment on a new Mac.

## SSH Setup
- [ ] Generate SSH key: `ssh-keygen -t ed25519 -C "your-email@example.com"`
- [ ] Add SSH key to GitHub: `cat ~/.ssh/id_ed25519.pub` then add at https://github.com/settings/keys
- [ ] Test connection: `ssh -T git@github.com`

## 1Password & Secrets
- [ ] **1Password** - Sign in to sync passwords
- [ ] **1Password CLI integration** - Open 1Password → Settings → Developer → enable "Integrate with 1Password CLI"
- [ ] **Generate secrets** - Run `cd ~/Git/toolbox/nixos && just secrets` (on headless hosts like dungeon, connect via VNC first: Finder → Go → Connect to Server)
- [ ] **Reddit session cookie** (hosts with pi) - pi-reddit-research needs one; Reddit has
      required auth on its `.json` endpoints since mid-2026. Deliberately *not* in 1Password —
      it expires every few days, and the file is re-read per request, so refreshing it needs no
      rebuild and no `just secrets`:
      ```
      mkdir -p ~/.config/pi-reddit-research
      # private window → reddit.com/login → F12 → Application → Cookies → reddit.com
      # copy the reddit_session (and token_v2) values
      printf 'reddit_session=VALUE; token_v2=VALUE\n' > ~/.config/pi-reddit-research/cookie.txt
      chmod 600 ~/.config/pi-reddit-research/cookie.txt
      ```
      Verify with a real tool call, not the slash command — in `-p` the model tends to look
      for `/reddit` in the repo instead of running it:
      ```
      pi -p 'Use the reddit_search tool to search Reddit for "nixos flakes". Report the count.'
      ```
      On **moria** this is a one-time step: `launchd.user.agents.reddit-cookie-sync`
      re-copies the cookie out of Firefox daily (`bin/reddit-cookie-sync.sh`), so it only
      needs your attention when it notifies you that Firefox is logged out — the fix then
      is just to log in at reddit.com in Firefox again. Elsewhere, redo it by hand whenever
      the tools start failing on auth.

## Application Logins
- [ ] **Firefox** - Sign in to Firefox Sync (Settings > Sync)
- [ ] **VS Code** - Sign in for Settings Sync (Cmd+Shift+P > "Settings Sync: Turn On")
- [ ] **Slack** - Sign in to workspaces
- [ ] **Discord** - Sign in
- [ ] **Spotify** - Sign in
- [ ] **Claude** - Sign in

## Repositories
- [ ] Clone notes repo: `git clone git@github.com:<user>/notes.git ~/Notes`
- [ ] Clone other personal repos as needed

## Frigate ANE Detector (dungeon only)
The `frigate-detector` launchd agent (hosts/macs/dungeon/default.nix) runs the native
Apple-Silicon object detector that Frigate connects to over ZMQ. It is not auto-cloned:
- [ ] `git clone https://github.com/frigate-nvr/apple-silicon-detector ~/Git/apple-silicon-detector`
- [ ] `cd ~/Git/apple-silicon-detector && /opt/homebrew/bin/python3.11 -m venv venv`
- [ ] `./venv/bin/pip3 install -r requirements.txt`
- [ ] Build & place the detection model (Frigate ships it to the detector over ZMQ; without it the
      agent runs but has no model). Recipe in the home-lab repo, `frigate/model-export/`:
      `docker build . --platform linux/amd64 --build-arg MODEL_SIZE=t --build-arg IMG_SIZE=320 --output . -f Dockerfile`
      then `cp yolov9-t-320.onnx "${SERVER_CONFIG_BASE}/frigate/model_cache/yolo.onnx"`
- [ ] Re-run `darwin-rebuild switch` so the agent finds the venv, then verify:
      `tail ~/Library/Logs/frigate-detector.log` shows "ZMQ server successfully bound to tcp://*:5555"

## Tier-1 Backup (dungeon only)
The `backup-tier1` launchd agent (hosts/macs/dungeon/default.nix) runs the home-lab script at
03:30 into two restic repositories. `restic` itself comes from homebrew-server.nix, but three
things cannot be expressed in nix and the agent fails — loudly, nightly — without them:
- [ ] Create the `Infra/restic` item in 1Password with a **strong, unique** repository password,
      then `cd ~/Git/home-lab && just secrets` to write `SECRET_RESTIC_PASSWORD`.
      ⚠️ This password is **not recoverable**. restic repositories are encrypted at rest, so a
      backup whose password is lost is indistinguishable from no backup at all. It lives in
      1Password specifically so it is not stored only on the machine being backed up.
- [ ] Authorise dungeon's SSH key on the offsite Pi: `ssh-copy-id -i ~/.ssh/id_rsa.pub pi@100.98.200.16`
      (run from dungeon; interactive, needs the Pi's password once).
- [ ] Verify both destinations answer before trusting the schedule:
      `ssh root@192.168.1.2 true && ssh fob true`
- [ ] Dry-run it, which stages everything but writes no repository:
      `cd ~/Git/home-lab && bash scripts/backup-tier1.sh --dry-run`
- [ ] Then one real run by hand, and confirm the Pushover notification arrives. Success is
      **not** silent here on purpose: the daily notification is the staleness detector, so if
      it ever stops arriving, that is the alert.

Restore procedure and failure triage: home-lab `docs/runbooks/backup-tier1.md`.

## Offsite backup of Unraid (dungeon only)
The `backup-offsite` (04:30), `backup-snapshot-probe` (09:00) and `backup-restore-drill`
(the 1st of each month, 10:00) launchd agents run the home-lab scripts of the same names.
They need nothing beyond
Tier 1's prerequisites: `restic`, `SECRET_RESTIC_PASSWORD`, dungeon's key on Unraid and fob.
B2 is optional and gated; setup in home-lab `docs/runbooks/backup-offsite.md` → Set up B2.

Until `darwin-rebuild switch` can run (it needs sudo), install them by hand with the same
plists nix would write. Then the next rebuild replaces them with identical ones.

```bash
for a in backup-offsite:-:4:30 backup-snapshot-probe:-:9:0 backup-restore-drill:1:10:0; do
  IFS=: read -r n d h m <<< "$a"
  day=""; [ "$d" = - ] || day="<key>Day</key><integer>$d</integer>"
  f=~/Library/LaunchAgents/org.nixos.$n.plist
  cat > "$f" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>org.nixos.$n</string>
	<key>ProgramArguments</key>
	<array>
		<string>/bin/bash</string>
		<string>/Users/ghilston/Git/home-lab/scripts/$n.sh</string>
	</array>
	<key>RunAtLoad</key>
	<false/>
	<key>StandardErrorPath</key>
	<string>/Users/ghilston/Library/Logs/$n.log</string>
	<key>StandardOutPath</key>
	<string>/Users/ghilston/Library/Logs/$n.log</string>
	<key>StartCalendarInterval</key>
	<array>
		<dict>
			$day
			<key>Hour</key>
			<integer>$h</integer>
			<key>Minute</key>
			<integer>$m</integer>
		</dict>
	</array>
</dict>
</plist>
EOF
  chmod 444 "$f"
  launchctl bootstrap gui/$(id -u) "$f"
done
launchctl list | grep -E 'backup-offsite|backup-snapshot-probe|backup-restore-drill'
```

Check by hand first: `cd ~/Git/home-lab && bash scripts/backup-offsite.sh --dry-run`
and `bash scripts/backup-snapshot-probe.sh --dry-run`. Each offsite repo is created once, by
hand: `bash scripts/backup-offsite.sh --init fob` (and `--init b2` once B2 is set up).
Then run the restore drill once rather than waiting for the 1st (it skips repos with no
snapshot yet): `bash scripts/backup-restore-drill.sh >> ~/Library/Logs/backup-restore-drill.log 2>&1`.
Full checklist, including the one-time fob mountpoint step: home-lab
`docs/runbooks/backup-offsite.md` → Deploy checklist.

## Claude Remote Control (dungeon; moria on demand)
The `claude-rc-<repo>` launchd agents (hosts/macs/dungeon/default.nix) serve toolbox,
home-lab, ccs, notes and blurts-server to the Claude app through `bin/claude-rc.sh`. On moria, `rc` starts
the same five in a background zellij session, and `zjk claude-rc` stops them. A server with
no TTY cannot answer a prompt, so do these once per host in a GUI session (VNC on dungeon):
- [ ] `claude` then `/login` with the Claude account. A `claude setup-token` token cannot
      serve Remote Control.
- [ ] In each of `~/Git/{toolbox,home-lab,ccs,notes,blurts-server}`, run `claude` once and accept the
      workspace trust dialog.
- [ ] Run `claude remote-control` once in any repo, answer `Enable Remote Control?` with `y`,
      then quit it.
- [ ] dungeon only: run `claude --permission-mode auto` once and accept the auto mode opt-in.
      moria's bypass mode needs no prompt: `skipDangerousModePermissionPrompt` is in the
      stowed settings.json.
- [ ] Verify: `tail ~/Library/Logs/claude-rc-home-lab.log` shows `Connected`, and the repos
      appear under the Code tab in the Claude app.

## Voice Input (Karabiner + FluidVoice)
Hold Caps Lock to dictate, or tap it to toggle hands-free; add Shift for a voice command,
Option for Write Mode (tap and hold work the same with either). Escape cancels a recording.
Until these are done Karabiner is inert and Caps Lock still toggles caps. On headless
dungeon (Karabiner only), do them over VNC. Background and per-host caveats:
`dot/karabiner/README.md`, `nixos/CLAUDE.md` → "FluidVoice".
- [ ] **Karabiner** - approve the driver extension (System Settings → Privacy & Security;
      may need a reboot), then grant Input Monitoring. Leave System Settings → Keyboard →
      Modifier Keys at its default — Karabiner's own remap supersedes it.
- [ ] **FluidVoice** (moria, citadel) - the first `just dr` opens it on onboarding. Grant
      Microphone and Accessibility (its hotkeys stay dead until Accessibility is on), and
      let it download the default Parakeet model. **Don't change the hotkeys** onboarding
      shows: nix seeded them (F18 dictate, F19 Command Mode, F20 Write Mode). Leave "Launch at login" off.
      > Starting it is *not* a manual step: `modules/darwin/fluidvoice.nix` launches it at
      > login (`launchctl list | grep org.nixos.fluidvoice`).
- [ ] **Fluid-1** (dictation polish) - AI Enhancement → Fluid Intelligence: download and
      verify it. On a fresh Mac, run `just dr <host>` once more after onboarding: the routing
      waits until onboarding is done. Nix already routes dictation to it, and Write and Command Mode to oMLX
      (`nixos/CLAUDE.md` → "FluidVoice"); oMLX's key comes from `just secrets`. Check with
      `tail -f ~/Library/Logs/Fluid/Fluid.log | grep processTextWithAI` while dictating: it
      should say `provider=fluid-1`. Its licence is personal, non-commercial use only.
      Command Mode asks before running each command; keep it so.
- [ ] **fluidvoice-ax** (moria, citadel) - allow it under System Settings → Privacy &
      Security → Accessibility when it asks (it is `fluidvoice-ax` in the list). Without it,
      Write Mode cannot read selected text in Slack, Obsidian or VS Code. After any edit to
      `modules/darwin/fluidvoice-ax.swift`, remove it from that list with "−" and allow it
      again: the grant is tied to the binary's hash and can look allowed while it is not.
      Check with `tail ~/Library/Logs/fluidvoice-ax.log`: `-> 0` per app is working,
      `-> -25211` is still waiting for the grant. For VS Code also set
      `"editor.accessibilitySupport": "on"` in its settings. Why: `nixos/CLAUDE.md` →
      "Write Mode in Electron apps".
- [ ] **Firefox** (moria, citadel) - quit and reopen it once after the first deploy, so it
      reads the accessibility policy nix set (it reads policies only at startup).
      `about:policies` should list `Preferences` → `accessibility.force_disabled`. Settings
      will now say the browser "is being managed by your organization"; that is this policy.
      Why, and why not the simpler `AXEnhancedUserInterface`: `nixos/CLAUDE.md` → "Write
      Mode in Firefox".
- [ ] **Handy** (moria, citadel) - after the first login following the deploy, quit it from
      the menu bar once. Its login item is still registered until that launch, which reads
      the `autostart_enabled = false` nix wrote and unregisters it. Until you quit it, it
      holds Option+Space (its default binding, which nix moved it back to).
- [ ] Smoke test, in order: holding Caps Lock shows FluidVoice's overlay and speaking
      inserts text at the cursor; a tap starts hands-free recording and another tap stops
      it; Shift + Caps Lock starts Command Mode (a tap keeps listening until a second
      Shift + Caps Lock tap); Option + Caps Lock starts Write Mode; Caps Lock never toggles
      caps on *any* attached keyboard (each one needs its own grab). If Shift or Option +
      Caps Lock does nothing, rebind that mode in FluidVoice's settings by pressing the chord.

## PI WEB (moria only)

`custom.programs.piWeb.enable` deploys the config, but the service is installed by hand.
It needs the network and a real login session for `launchctl bootstrap`, neither of which
nix activation has — and `pi-web install` regenerates its own launchd plists every run, so
anything nix declared there would be replaced or fail `pi-web doctor`.
See `modules/darwin/pi-web.nix`.

- [ ] **Install** - `cd ~/Git/toolbox/nixos && just pi-web-setup`. Re-running is safe and is
      also the upgrade path: pi-web replaces its services rather than duplicating them.
- [ ] **Verify** - `pi-web doctor` reports both `com.pi-web.web` and `com.pi-web.sessiond`
      healthy, and `curl -sI http://$(tailscale ip -4):8504/` returns 200
      > Straight after a cold boot this can look broken: the services bind to moria's
      > tailnet address, which does not exist until tailscaled has come up. The agents are
      > `RunAtLoad` with `KeepAlive{SuccessfulExit:false}`, so they retry on their own —
      > give it a moment before believing `doctor`.
- [ ] **Reach it remotely** - https://pi.grehg2.xyz over Tailscale, routed by Caddy on
      dungeon (see `~/Git/home-lab/caddy/Caddyfile`). PI WEB has **no authentication** of its
      own — the tailnet is the only thing keeping it private, which is why it binds to
      moria's tailnet address and not 0.0.0.0
- [ ] **Add a project** - point it at `~/Git`, start a session, close the tab and reopen it
      to confirm the session survived

## Hermes Desktop (moria, citadel)

Hermes runs only on dungeon (home-lab `hermes/`). These Macs are Desktop clients of it,
over Tailscale at `https://hermes.grehg2.xyz`. `just dr` installs the cask and, through
`modules/darwin/hermes-desktop.nix`, makes that URL the primary gateway in
`~/Library/Application Support/Hermes/connections.json`.

**The cask only stages an installer.** `Hermes.app` holds one `Hermes-Setup` binary, and
there is no app data until it has run, so the registration waits for it:

- [ ] `open -a Hermes` once, then `just dr <host>` again so the gateway entry lands
- [ ] Desktop → Settings → Gateway → **Sign in** to `dungeon`: user `greg`, password
      `Infra/Hermes` → `dashboard_password`. Nix writes no credential; the session is the app's
- [ ] Tailscale is up (`tailscale status`); off the tailnet the name does not resolve

**No messaging gateway may run on these Macs.** Two Telegram pollers on one bot token each
get a random share of the updates. `just dr` warns while a gateway agent or a chat token is
still here.

### One-time cutover from moria's own Hermes

Do these on moria, in this order. **moria's gateway stops before dungeon starts polling
Telegram.**

- [ ] Stop and remove the gateway: `hermes gateway stop && hermes gateway uninstall`, then
      `launchctl list | grep -i hermes` and `pgrep -fl hermes_cli` print nothing
- [ ] Archive the history (it is archived, not migrated). The runtime and node are left out
      because the Desktop app still uses them:
      ```bash
      tar -C ~ --exclude .hermes/hermes-agent --exclude .hermes/node \
        -czf ~/hermes-moria-$(date +%F).tar.gz .hermes
      ```
- [ ] Remove what the old server used: `~/.hermes/profiles/`, `~/.hermes/.env*`, `~/.hermes/mode`,
      and the symlinks into toolbox (`config.yaml`, `SOUL.md`, `hooks`, and the `lab-tools`
      links under `skills/`), which now dangle
- [ ] Deploy dungeon's Hermes (home-lab), which takes over Telegram
- [ ] `just dr moria`, then sign in as above. No warning at the end means no gateway is left

## Launch Applications

- [ ] Set up AeroSpace tiling
- [ ] **Vorssaint** (moria, citadel) - the menu-bar utility suite. Like FluidVoice, it is launched
      at login by `modules/darwin/vorssaint.nix`, and like it, it also seeds its own
      Features hub, so there is nothing to pick on first launch — only permissions to grant.
      Leave its Settings → "Launch at login" **off**; the launchd agent owns that.
      Grant these, in rough order of how much stops working without them:
      - **Accessibility** — the app switcher, Dock previews, quit-on-close, ⌘X/⌘V in
        Finder, paste-as-plain-text, the volume mixer and external-display brightness.
        This is the one that matters.
      - **Screen Recording** — the switcher's and Dock preview's window thumbnails, plus
        the screenshot, screen-recording and copy-text-from-screen tools.
      - **System Audio Recording** — per-app volume and per-app output. Without it every
        app just rides the normal system output.
      - **Automation → Finder** — ⌘X/⌘V in Finder.
      - **Camera** — the camera preview mirror. **Microphone** — the optional voice track
        in screen recordings. Both prompt the first time you use them.
      > Nothing is broken while a grant is missing — a feature that needs one sits inert
      > and says so on Vorssaint's own Permissions page, which also lists which features
      > use each grant. Nothing here can be declared: TCC is outside nix's reach.
- [ ] Confirm the seed ran. It happens during `just dr` itself, after Homebrew, so the
      output is in the rebuild's own log: `seeding the Features hub with mixer, switcher,
      …` the first time and `already set up, leaving the Features hub alone` on every
      rebuild after. A `WARNING: the Vorssaint seed did not finish` line means it fell
      back to the app's own wizard — the rebuild is not failed by it.
      > To re-seed deliberately after editing the feature list — it is otherwise a
      > once-per-Mac write, so an edit alone changes nothing on a host already set up:
      > ```
      > osascript -e 'quit app "Vorssaint"'
      > defaults delete com.vorssaint.utils hasOnboarded
      > just dr <host>
      > ```
