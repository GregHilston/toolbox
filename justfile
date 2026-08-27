set shell := ["zsh", "-cu"]

# Set up Claude Code symlinks (commands, skills, CLAUDE.md, settings, hooks, ccstatusline)
# for the current user, and install the pinned ccstatusline.
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

    # ccstatusline keeps its config outside ~/.claude, and its TUI writes back to it.
    mkdir -p "$HOME/.config/ccstatusline"
    link_repo "$repo/dot/ccstatusline/.config/ccstatusline/settings.json" "$HOME/.config/ccstatusline/settings.json"

    # Keep this pin in sync with ccstatuslineVersion in
    # nixos/modules/programs/tui/claude.nix (the source of truth for Nix hosts).
    ccstatusline_version="2.2.27"
    npm_prefix="$HOME/.npm-global"
    if command -v npm >/dev/null 2>&1; then
        installed="$(jq -r .version "$npm_prefix/lib/node_modules/ccstatusline/package.json" 2>/dev/null || true)"
        if [ ! -x "$npm_prefix/bin/ccstatusline" ] || [ "$installed" != "$ccstatusline_version" ]; then
            echo "Installing ccstatusline $ccstatusline_version into $npm_prefix..."
            npm install -g --prefix "$npm_prefix" "ccstatusline@$ccstatusline_version" \
                || echo "WARNING: ccstatusline install failed (offline?)." >&2
        fi
    else
        echo "WARNING: npm not found — skipping ccstatusline install; the status line will be blank." >&2
    fi

# Run both test suites: the pi extensions (TypeScript, node --test) and the
# bin/ scripts (Python, stdlib unittest). Neither needs a build step or a
# dependency install.
test:
    #!/usr/bin/env zsh
    set -eu
    repo="$(pwd)"
    echo "== pi extensions =="
    ( cd "$repo/dot/pi" && node --test 'tests/*.test.ts' )
    echo "== bin/ scripts =="
    ( cd "$repo/tests" && python3 -m unittest discover -s . -p 'test_*.py' )
