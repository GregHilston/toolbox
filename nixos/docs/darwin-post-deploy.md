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

## Voice Input (Karabiner + Handy)
Hold Caps Lock to dictate; a quick tap is Escape. Until these are done Karabiner is inert
and Caps Lock still toggles caps. On headless dungeon, do them over VNC. Background and
per-host caveats: `dot/karabiner/README.md`.
- [ ] **Karabiner** - approve the driver extension (System Settings → Privacy & Security;
      may need a reboot), then grant Input Monitoring. Leave System Settings → Keyboard →
      Modifier Keys at its default — Karabiner's own remap supersedes it.
- [ ] **Handy** - grant Microphone and Accessibility (needed to paste into the focused app),
      then download a model: Parakeet V3 (CPU-efficient English) or Whisper Turbo/Large
      (better accuracy, 100+ languages)
      > Starting Handy is *not* a manual step: `modules/darwin/handy.nix` launches it at
      > login (`launchctl list | grep org.nixos.handy`). Leave Handy's own "Launch at
      > login" setting off so the two don't both register it.
- [ ] **Handy hotkey** - set the binding to `F18` by *holding* Caps Lock while the picker is
      capturing, and leave push-to-talk mode on (its default). It will display and store this
      as `fn + F18` — that's correct, macOS flags all F-keys with `fn`
- [ ] Smoke test, in order: a quick Caps Lock tap sends Escape; holding it opens Handy's
      recording overlay and speaking inserts text at the cursor; Caps Lock never toggles caps
      on *any* attached keyboard (each one needs its own grab)

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

## Launch Applications

- [ ] Set up AeroSpace tiling
- [ ] **Ice** (menu bar manager, replaced Bartender) - it's launched at login by the launchd
      agent in `modules/darwin/ice.nix`, but its permissions are GUI-gated: on first launch
      approve Accessibility (move/hide menu bar items) and Screen Recording (item search and
      menu bar appearance). Leave Ice's own Settings → General → "Launch Ice at login"
      **off** — the launchd agent owns that, and both would double-register.
- [ ] Arrange the menu bar in Ice: drag icons above/below the divider with ⌘-drag to choose
      what stays visible vs. hidden
