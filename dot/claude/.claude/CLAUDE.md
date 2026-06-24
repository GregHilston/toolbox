Never add "Generated with [Claude Code] or co-authored by claude in the commit messages we generate together.

If I ever ask you to generate a PR description, do so by writing markdown to a file.

@RTK.md

## Pixel 8 (Termux)

Shared storage path: `/data/data/com.termux/files/home/storage/shared/Git/`
- Notes repo: `shared/Git/notes/`
- SSH: port 8022, user `u0_a305`, IP in `~/.ssh/config`

## Documentation Philosophy

When writing or updating any CLAUDE.md or README:
- **Point to the directory, not its contents.** One sentence on what it's for is enough — never enumerate every file or script. Claude can always explore with Glob/ls when it needs to.
- This prevents documentation rot: files change, tables go stale, context bloats.

## File Inspection

Prefer the `Read`, `Grep`, and `Glob` tools over shelling out to `cat`/`head`/`tail`/`sed`/`grep` for inspecting files — they return cleaner, line-numbered, structured output and fail less. Reserve Bash for things that genuinely need it (running builds/tests, `git`, `nix`, etc.).

## Toolbox

`~/Git/toolbox` holds my dotfiles, scripts, and host configs. Its `bin/**` is on `$PATH` (recursive zsh glob), so helpers like `fetch-thread.py` work from any repo. See `~/Git/toolbox/CLAUDE.md` for details.
