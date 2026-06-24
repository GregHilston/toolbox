set shell := ["zsh", "-cu"]

# Set up Claude Code symlinks (commands, skills, CLAUDE.md, settings, hooks) for the current user.
# Run this once on any non-Nix host (Nix hosts get this automatically via home-manager).
setup-claude:
    #!/usr/bin/env zsh
    set -eu
    mkdir -p "$HOME/.claude"
    repo="$(pwd)"

    # link_repo SRC DST — mirror of nixos/modules/programs/tui/claude.nix:
    #   symlink -> refresh; missing -> create; real file -> warn and skip (don't clobber).
    link_repo() {
        if [ -L "$2" ]; then
            ln -sfn "$1" "$2"
            echo "Refreshed $2 -> $1"
        elif [ ! -e "$2" ]; then
            ln -s "$1" "$2"
            echo "Linked $2 -> $1"
        else
            echo "WARNING: $2 is a real file, not a symlink — leaving it untouched." >&2
            echo "  Migrate it into $1, delete the original, then re-run." >&2
        fi
    }

    link_repo "$repo/claude-commands"             "$HOME/.claude/commands"
    link_repo "$repo/claude-skills"               "$HOME/.claude/skills"
    link_repo "$repo/dot/claude/.claude/CLAUDE.md"     "$HOME/.claude/CLAUDE.md"
    link_repo "$repo/dot/claude/.claude/settings.json" "$HOME/.claude/settings.json"
    link_repo "$repo/dot/claude/.claude/hooks"         "$HOME/.claude/hooks"
