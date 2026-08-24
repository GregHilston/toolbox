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

## Bash working directory — use absolute paths

**The Bash tool's cwd persists between calls, and it is almost never where you
assume.** A `cd` in one call silently changes the meaning of every relative path
in later calls, including calls made much later in the conversation.

Use an absolute path — or lead with `cd /abs/path &&` — for anything where being
in the wrong directory produces a *wrong answer* rather than an error:

- `git worktree add worktrees/foo` creates the worktree relative to cwd. Run
  from a subdirectory, it silently nests one inside your project.
- `git merge <branch>` run from inside that branch's own worktree reports
  "Already up to date" and merges nothing.
- `git status --porcelain <path>` with a path that does not exist from cwd
  prints a warning to stderr and **exits 0 with no output**, so a check like
  `git status --porcelain x/ && echo CLEAN` reports success for a directory it
  never looked at. Verification commands are the worst place for this, because
  the failure mode is a false pass.

The tell is an error naming a path with a doubled or missing prefix
(`api-backend/tests/goldens/`, `can't open file ROADMAP.md`). Treat that as a
cwd problem first, not a missing-file problem.

## File Inspection

Prefer the `Read`, `Grep`, and `Glob` tools over shelling out to `cat`/`head`/`tail`/`sed`/`grep` for inspecting files — they return cleaner, line-numbered, structured output and fail less. Reserve Bash for things that genuinely need it (running builds/tests, `git`, `nix`, etc.).

## Toolbox

`~/Git/toolbox` holds my dotfiles, scripts, and host configs. Its `bin/**` is on `$PATH` (recursive zsh glob), so helpers like `fetch-thread.py` work from any repo. See `~/Git/toolbox/CLAUDE.md` for details.

## Researching Reddit

Two steps, both in `~/Git/toolbox/bin`:

1. **`reddit-search.py "<query>"`** — finds threads (`-r <sub>` repeatable to scope,
   `-s`/`-t` for sort and time window, `--format json`).
2. **`fetch-thread.py <url>`** — prints one thread's post + threaded comments.
   Works for Hacker News too.

**Do not use Reddit's `search.json`, and do not trust pi's `reddit_search`,
`reddit_pack` or `reddit_trends`.** That endpoint answers HTTP 200 with an empty
`children` array rather than failing, so everything built on it silently returns
nothing. `reddit-search.py` exists because of this: it scrapes old.reddit.com's HTML
search, which still works and still carries score, comment count, author, date and a
body snippet. Listing endpoints and thread permalinks were never affected.

`reddit-cookie-sync.sh` reports OK regardless, because it probes a *listing* — a
healthy cookie is not evidence that search works. A 403 (rather than empty results)
*is* the cookie: log into reddit.com **in Firefox**, then run that script.

**Don't reach for `searxngr` to find Reddit threads.** It was the old workaround and
it no longer earns its place — the self-hosted instance's egress IP is blocked by
every engine that indexes Reddit deeply (DuckDuckGo and Startpage CAPTCHA, Brave
rate-limits, Google and Mojeek return nothing), leaving only Bing, which serves it
results unrelated to the query. `WebSearch` is the reliable general-web fallback.
