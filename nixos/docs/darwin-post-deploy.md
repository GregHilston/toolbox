# Darwin Post-Deploy Checklist

Run these tasks after initial deployment on a new Mac.

## SSH Setup
- [ ] Generate SSH key: `ssh-keygen -t ed25519 -C "your-email@example.com"`
- [ ] Add SSH key to GitHub: `cat ~/.ssh/id_ed25519.pub` then add at https://github.com/settings/keys
- [ ] Test connection: `ssh -T git@github.com`

## Application Logins
- [ ] **1Password** - Sign in to sync passwords
- [ ] **Firefox** - Sign in to Firefox Sync (Settings > Sync)
- [ ] **VS Code** - Sign in for Settings Sync (Cmd+Shift+P > "Settings Sync: Turn On")
- [ ] **Slack** - Sign in to workspaces
- [ ] **Discord** - Sign in
- [ ] **Spotify** - Sign in
- [ ] **Claude** - Sign in
- [ ] **Obsidian** - Sign in (if using Obsidian Sync)

## Repositories
- [ ] Clone notes repo: `git clone git@github.com:<user>/notes.git ~/Notes`
- [ ] Clone other personal repos as needed

## Optional
- [ ] Configure Raycast preferences
- [ ] Set up AeroSpace tiling (if using)
- [ ] Configure Bartender menu bar layout
