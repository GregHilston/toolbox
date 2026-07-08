# Claude Code Docker Setup

This directory contains a Docker setup for running Claude Code in an isolated container that shares your host authentication and session history.

## Reference Implementation

This setup is based on the official Claude Code devcontainer:
- **Documentation**: https://code.claude.com/docs/en/devcontainer
- **Reference Repository**: https://github.com/anthropics/claude-code/tree/main/.devcontainer

## Key Files

- **Dockerfile** — Based on the official reference. Installs Claude Code CLI and development tools in a Node.js 20 container, running as the non-root `node` user.

## Setup

No manual setup is required — the `claude-docker` shell function builds the
image on first run if it isn't present. To build (or rebuild) it by hand:

```bash
cd ~/Git/toolbox/claude-code
docker build -t my-claude-code:latest .
```

## Usage

The `claude-docker` function is defined in `dot/zsh/.zshrc`:

```bash
# Start a new session or resume the default one
claude-docker

# Resume a specific past session
claude-docker --resume SESSION_ID
```

Under the hood it runs (see the function for the authoritative version):

```bash
docker run --rm -it \
  -v ~/.claude:/home/node/.claude \
  -v "$git_home:$git_home" \
  -w "$PWD" \
  -u "$(id -u):$(id -g)" \
  -e HOME=/home/node \
  -e CLAUDE_CONFIG_DIR=/home/node/.claude \
  my-claude-code:latest \
  code --dangerously-skip-permissions "$@"
```

## How Persistence Works

- **Bind mount**: `-v ~/.claude:/home/node/.claude` mounts your real host
  `~/.claude` into the container, so credentials, settings, and session
  history are shared directly with the host (not isolated in a Docker volume).
- **Matching paths**: Claude Code encodes the working directory into project
  identifiers. `~/Git` is mounted at its actual host path (not `/workspace`)
  and `-w "$PWD"` matches the host cwd, so a project has the same identity
  inside and outside the container — sessions started on the host resume in
  the container and vice versa.
- **Host user**: `-u host_uid:host_gid` (with `HOME=/home/node`) means files
  created in the container are owned by you, not root.

## Differences from Official Reference

The official reference includes:
- Bash history persistence (optional for CLI-only use)
- Firewall script for network egress control (optional)
- Zsh with Powerline10k theme (included here)
- VS Code extensions (not applicable for CLI-only use)

This implementation includes the essentials: Claude Code CLI, git, Python, zsh, and shared host authentication.

## Troubleshooting

**"Image not found"**: The function auto-builds on first run; to force a rebuild, `docker build -t my-claude-code:latest .` from this directory.

**"Permission denied on ~/.claude"**: The container runs as your host UID/GID; ensure your host `~/.claude` is owned by you.

**"Need to access files from host"**: Everything is a bind mount — `~/.claude` and your `~/Git` tree are the real host directories, editable from either side.
