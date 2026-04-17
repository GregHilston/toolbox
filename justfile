set shell := ["zsh", "-cu"]

# Set up Claude Code commands and skills symlinks for the current user
# Run this once on any non-Nix host (Nix hosts get this automatically via home-manager)
setup-claude:
    #!/usr/bin/env zsh
    set -eu
    mkdir -p "$HOME/.claude"

    if [ ! -e "$HOME/.claude/commands" ]; then
        ln -sf "$(pwd)/claude-commands" "$HOME/.claude/commands"
        echo "Linked ~/.claude/commands -> $(pwd)/claude-commands"
    else
        echo "~/.claude/commands already exists, skipping"
    fi

    if [ ! -e "$HOME/.claude/skills" ]; then
        ln -sf "$(pwd)/claude-skills" "$HOME/.claude/skills"
        echo "Linked ~/.claude/skills -> $(pwd)/claude-skills"
    else
        echo "~/.claude/skills already exists, skipping"
    fi
