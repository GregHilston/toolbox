# Darwin Manual Setup Steps

The following steps must be completed manually after the initial `nix-darwin` activation. These cannot be automated via the declarative configuration.

## 1. VMware Fusion

VMware Fusion must be downloaded manually from Broadcom's support portal (the Homebrew cask is disabled).

1. Create a Broadcom account at <https://support.broadcom.com>
2. Navigate to **VMware Fusion** under your registered products
3. Download and install the latest version

## 2. SSH Keys

Generate or restore SSH keys for GitHub, remote hosts, etc.

```bash
ssh-keygen -t ed25519 -C "your-email@example.com"
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

Then add the public key to GitHub, GitLab, or any remote hosts as needed.

## 3. Environment File

Create a `~/.env` file with any secrets or environment variables not managed by nix-darwin:

```bash
touch ~/.env
# Add variables as needed
```
