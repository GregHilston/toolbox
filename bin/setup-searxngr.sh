#!/bin/bash
# Setup searxngr CLI for searching local SearXNG instance
# Installs searxngr via uv and stows config from ~/Git/toolbox/dot/searxngr

set -e

echo "Installing searxngr via uv..."
uv tool install --upgrade https://github.com/scross01/searxngr.git

echo "Setting up searxngr configuration via stow..."
cd ~/Git/toolbox/dot
stow -t "$HOME" searxngr-config

echo "✓ searxngr installed and configured"
echo "✓ Configuration file: ~/.config/searxngr/config.ini (managed by stow)"
echo "✓ SearXNG URL: https://searxng.grehg2.xyz (dungeon instance via Tailscale)"
echo ""
echo "Usage:"
echo "  searxngr query                    # Search your local SearXNG"
echo "  searxngr --category reddit query  # Search Reddit-specific results"
echo "  searxngr --json query             # JSON output for scripting"
