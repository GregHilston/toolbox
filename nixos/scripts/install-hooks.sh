#!/usr/bin/env bash
# Install git hooks for NixOS configuration validation
#
# Usage: ./nixos/scripts/install-hooks.sh
#
# This installs:
# - pre-commit: Runs nix fmt on staged .nix files
# - pre-push: Validates all NixOS configs using the devcontainer

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"
SOURCE_DIR="$SCRIPT_DIR/hooks"

echo "Installing git hooks..."

# Install pre-commit hook
if [ -f "$HOOKS_DIR/pre-commit" ]; then
    echo "Backing up existing pre-commit hook to pre-commit.backup"
    mv "$HOOKS_DIR/pre-commit" "$HOOKS_DIR/pre-commit.backup"
fi
cp "$SOURCE_DIR/pre-commit" "$HOOKS_DIR/pre-commit"
chmod +x "$HOOKS_DIR/pre-commit"
echo "Installed: pre-commit (nix fmt)"

# Install pre-push hook
if [ -f "$HOOKS_DIR/pre-push" ]; then
    echo "Backing up existing pre-push hook to pre-push.backup"
    mv "$HOOKS_DIR/pre-push" "$HOOKS_DIR/pre-push.backup"
fi
cp "$SOURCE_DIR/pre-push" "$HOOKS_DIR/pre-push"
chmod +x "$HOOKS_DIR/pre-push"
echo "Installed: pre-push (full validation)"

echo ""
echo "Git hooks installed successfully!"
echo ""
echo "Hooks will run automatically:"
echo "  - pre-commit: Formats .nix files with 'nix fmt'"
echo "  - pre-push: Validates all configs via devcontainer"
echo ""
echo "To skip hooks (not recommended):"
echo "  git commit --no-verify"
echo "  git push --no-verify"
