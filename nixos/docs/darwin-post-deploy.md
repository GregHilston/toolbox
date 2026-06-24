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

## Launch Applications

- [ ] Set up AeroSpace tiling
- [ ] Configure Bartender menu bar layout
