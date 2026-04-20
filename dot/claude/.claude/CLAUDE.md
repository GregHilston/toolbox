Never add "Generated with [Claude Code] or co-authored by claude in the commit messages we generate together.

If I ever ask you to generate a PR description, do so by writing markdown to a file.

@RTK.md

## Documentation Philosophy

When writing or updating any CLAUDE.md or README:
- **Point to the directory, not its contents.** One sentence on what it's for is enough — never enumerate every file or script. Claude can always explore with Glob/ls when it needs to.
- This prevents documentation rot: files change, tables go stale, context bloats.

## Toolbox (`~/Git/toolbox`)

Personal dotfiles, scripts, and configs. Key directories:
- `bin/` — utility scripts; all subdirectories also on `$PATH` via recursive zsh glob
- `bin/anki/` — Anki database management scripts (PEP 723, `uv run`)
- `dot/` — dotfiles managed with GNU Stow; `just stow-all` from `dot/` sets everything up on a new machine
- `claude-commands/` — Claude Code slash commands (symlinked to `~/.claude/commands`)
- `claude-skills/` — Claude Code skills (symlinked to `~/.claude/skills`)
