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

## Launch Applications

- [ ] Set up AeroSpace tiling
- [ ] **Ice** (menu bar manager, replaced Bartender) - it's launched at login by the launchd
      agent in `modules/darwin/ice.nix`, but its permissions are GUI-gated: on first launch
      approve Accessibility (move/hide menu bar items) and Screen Recording (item search and
      menu bar appearance). Leave Ice's own Settings → General → "Launch Ice at login"
      **off** — the launchd agent owns that, and both would double-register.
- [ ] Arrange the menu bar in Ice: drag icons above/below the divider with ⌘-drag to choose
      what stays visible vs. hidden
