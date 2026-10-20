# Global instructions for pi

Hand-maintained port of the parts of `~/.claude/CLAUDE.md` that apply to pi. pi does
not read that file. Edit both when a rule changes.

## No AI attribution, anywhere

Never add a `Co-Authored-By` trailer, a "Generated with" line or any session link to
a commit message, PR title, PR description, issue or code comment. If asked for a PR
description, write markdown to a file.

## Writing code

- **Comments carry why, never what.** Keep one only for a non-obvious constraint, a
  deliberate deviation or a gotcha. Default to none. Seven words or fewer per block.
- **Never narrate a change in code.** No "was/now/previously" or "this fixes". That
  belongs in the commit message.
- **Simplicity beats completeness.** No speculative abstraction, caching or guardrail
  nobody asked for.
- Watch for state derived from other state, duplicated conditionals, leaky
  abstractions across layers, and repeated work.

## Prose

Active voice. No stage performances. Pick the commonest word.

When you write a CLAUDE.md, AGENTS.md or README, point to a directory and say in one
sentence what it is for. Never list its files; they go stale.

## Shell gotchas

- The shell is zsh. An unquoted `$var` does not word-split.
- The working directory persists between calls. Use absolute paths, or lead with
  `cd /abs/path &&`, for `git worktree add`, `git merge` and any check where the
  wrong directory gives a wrong answer instead of an error. `git status --porcelain
  <missing path>` exits 0 with no output, a false pass.
- Prefer the read, grep and find tools over `cat`, `sed` and `grep` in the shell.

## Machines

- **moria** (M4 Max, 128 GB) is the dev machine. Use all its hardware.
- **dungeon** (M3 Pro, 48 GB, RAM nearly full) runs home-lab services that must not
  be interrupted. Put no build or test load on it.
- `~/Git/toolbox` holds dotfiles, scripts and host configs. Its `bin/` is on `$PATH`.

## Working with me

- I often read on my phone. Keep status to short bullets and lead with what changed.
- Answer a mid-task message in your very next reply.
- When you need a decision, use `ask_user_question` and put the recommended option first.

## Research

- Reddit: `reddit-search.py "<query>"` finds threads, `fetch-thread.py <url>` reads
  one (also Hacker News). No login. Do not use `searxngr` for Reddit.
- Notes written for `~/Git/notes` go in its `llm/` folder with a `topics:` property,
  never at the vault root.

## When Claude is unavailable (fallback mode)

You are probably here because Anthropic is down, the internet is down, or dungeon is
down. Work read-only by default: diagnose, then propose a fix and ask before acting.

- Home-lab alerts or "what is broken": run `lab-alerts`, then use the `oncall` skill
  for one alert, `triage` for a full sweep, `post-reboot` after dungeon restarts.
- Network trouble (no DNS, no internet, tailnet down): run `netcheck`.
- A service name (sabnzbd, sonarr, plex, nextcloud, grafana…) means Greg's own copy at
  `https://<name>.grehg2.xyz`, never the public project. Check it with `lab-alerts` and
  `curl -sS -o /dev/null -w '%{http_code}' <url>`. Never use a public status site.
- Runbooks live in `~/Git/home-lab/docs/runbooks/`; `README.md` there is the index.
  Read the matching runbook before you run anything.
- Watchdog and backup logs live on dungeon, not here:
  `ssh dungeon tail -n 50 ~/Library/Logs/<name>.log`.
- **State a cause only when a command output or a doc line shows it.** Otherwise say
  "possibly", and name the check that would confirm it. Two alerts firing together do
  not prove one caused the other.
- The default model, `litellm/local-small`, goes through the gateway on dungeon. If
  dungeon or DNS is down, it fails. Switch with `/model` to `omlx/Qwen3.6-35B-A3B-4bit`
  (localhost:8000, 262k window, runs on moria only).
- Every `litellm/*` model, `litellm/cloud` included, goes through dungeon.
  `litellm/cloud` and `deepseek/*` also need the internet.
- What each tool needs: `netcheck` and file work need nothing. `lab-alerts`,
  `ha-state.py` and `web_search` need dungeon. Web search, web fetch, Reddit, weather
  and Wikipedia also need the internet.
- Local models are slower and weaker than Claude. Keep steps small and check each result.

## Agent skills

### Writing a skill or an agent tool

Follow `~/Git/toolbox/skills/README.md`: one skill set for Claude Code, pi and
Hermes, with the tool itself a script in `~/Git/toolbox/bin/`.

### Issue tracker

Run `git config wayfinder.tracker`. `github` means GitHub Issues: follow
`~/.claude/skills/setup-matt-pocock-skills/issue-tracker-github.md`. `local` means
markdown files under `.scratch/`: follow
`~/.claude/skills/setup-matt-pocock-skills/issue-tracker-local.md`. If it is unset,
ask which of the two this repo should use, then store the answer with
`git config wayfinder.tracker <answer>` first. A repo's own CLAUDE.md or AGENTS.md
block overrides this. If a label a skill applies does not exist, `gh label create` it.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the repo root. Follow
`~/.claude/skills/setup-matt-pocock-skills/domain.md`.
