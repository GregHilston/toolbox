# Claude Code Custom Commands

This directory contains reusable custom commands that can be used across projects with Claude Code.

## Setup

To use these commands, symlink this directory to `~/.claude/commands`:

```bash
# Symlink it to where Claude Code looks
ln -s ~/Git/toolbox/claude-commands ~/.claude/commands
```

**Note**: If `~/.claude/commands` already exists as a regular directory, you'll need to back it up first:

```bash
# Backup existing commands (if any)
mv ~/.claude/commands ~/.claude/commands.backup

# Then create the symlink
ln -s ~/Git/toolbox/claude-commands ~/.claude/commands
```

## Verify Setup

After symlinking, verify it worked:

```bash
ls -la ~/.claude/commands
```

You should see output like:
```
lrwxr-xr-x  ... /Users/you/.claude/commands -> /Users/you/Git/toolbox/claude-commands
```

The `l` at the start indicates it's a symlink, and the `->` shows where it points.

## Usage

Once symlinked, all `.md` files in this directory become available as custom commands in Claude Code. The filename becomes the command name (e.g., `handoff.md` → `/handoff`).

## Project-Specific Commands

For commands specific to a single project, you can also create `.claude/commands/` within that project's directory. Commands there will be available alongside these global commands when working in that project.
