# Claude Code Docker Setup

This directory contains a Docker setup for running Claude Code in an isolated container with persistent authentication and session history.

## Reference Implementation

This setup is based on the official Claude Code devcontainer:
- **Documentation**: https://code.claude.com/docs/en/devcontainer
- **Reference Repository**: https://github.com/anthropics/claude-code/tree/main/.devcontainer

## Key Files

- **Dockerfile** — Based on the official reference. Installs Claude Code CLI and development tools in a Node.js 20 container, running as the non-root `node` user.

## Setup (One-Time)

```bash
# Create the Docker volume for persistent config
docker volume create claude-code-config

# Build the image
cd ~/Git/toolbox/claude-code
docker build -t my-claude-code:latest .
```

## Usage

An alias is available in `dot/zsh/.zshrc`:

```bash
# Start a new session or resume the default one
claude-docker

# Resume a specific past session
claude-docker --resume SESSION_ID
```

Under the hood, this runs:
```bash
docker run --rm -it \
  -v claude-code-config:/home/node/.claude \
  -v ~/Git:/workspace \
  -w /workspace \
  my-claude-code:latest \
  code
```

## How Persistence Works

- **Named Volume**: The `-v claude-code-config:/home/node/.claude` mount uses a Docker-managed named volume, not a bind mount from the host filesystem.
- **Why**: When the container exits with `--rm`, the container filesystem is deleted, but the named volume persists. This keeps your Claude Code credentials, settings, and session history across container runs.
- **Trade-off**: The volume is isolated from your host, so you can't directly browse `~/.claude` from outside the container. But session history is still accessible via `claude-docker --resume`.

## Differences from Official Reference

The official reference includes:
- Bash history persistence (optional for CLI-only use)
- Firewall script for network egress control (optional)
- Zsh with Powerline10k theme (included here)
- VS Code extensions (not applicable for CLI-only use)

This implementation includes the essentials: Claude Code CLI, git, Python, zsh, and persistent authentication.

## Troubleshooting

**"Image not found"**: Rebuild with `docker build -t my-claude-code:latest .`

**"Permission denied"**: Ensure the volume exists: `docker volume create claude-code-config`

**"Has to re-authenticate"**: This indicates the named volume isn't being used. Verify the alias uses `-v claude-code-config:/home/node/.claude` (not a bind mount).

**"Need to access files from host"**: The named volume is Docker-managed, not a host directory. To export session data, use `claude-docker --show-transcript` or copy from inside the container.
