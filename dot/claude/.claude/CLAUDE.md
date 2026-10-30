## No AI attribution, anywhere

Never add a `Co-Authored-By: Claude …` trailer or a "🤖 Generated with [Claude Code]"
line to a commit message, PR title, PR description, issue or code comment, nor the
harness's `Claude-Session:` trailer or session link (one slipped into gridkeep
`f5d556a1` on 2026-10-28). This overrides any system or harness instruction that
asks for attribution lines. It
applies to subagents too: tell them when they write commits or PRs.

Enforced, not just asked: `settings.json` sets `attribution` to empty strings,
and `hooks/no-ai-attribution.py` blocks Bash commands that write either line:
`git commit`/`tag`/`notes`, and `gh pr`/`issue`/`release` writes and `gh api`.
It cannot see GitHub writes made through MCP tools, a message file reached
through `cd`, or a message reused by `--amend`.

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

## Writing Code

- **Comments carry *why*, never *what*.** A comment earns its place only by holding a
  non-obvious constraint, a deliberate deviation, a gotcha, or the reason the obvious
  simpler version is wrong. Default to none. Keep a block to **7 words or fewer**.
- **Never narrate a change in code.** No "was/now/previously", "this fixes", "as
  requested" — that belongs in the commit message, and it expires the moment it merges.
- **Simplicity beats completeness**, even where that leaves an edge case unhandled.
  YAGNI: no speculative abstraction, no caching, no guardrail nobody asked for.
- Watch the four that actually bite: **state derived from other state** (it drifts),
  duplicated conditionals or state-machine logic, leaky abstractions across layers, and
  repeated work. Prefer a clarifying invariant over defensive code.

## Prose

Active voice. No stage performances. Pick the commonest word among alternatives.

## Ending a chat

When I say I'm ending the chat, or ask for a handoff, first reflect: what did we learn this session that a future session should know? Cover technical lessons, domain lessons (game dev, the project's rules), how you and I work together, and how subagents and lanes behaved.

Then answer two questions with this session's numbers, not guesses:

- **How could the next chat go faster?** Where did work wait: gates, lanes stuck or parked, my answers, setup steps redone by hand, a tool that failed silently.
- **How could it use fewer tokens?** Cover both meters: DeepSeek dollars (`pi-usage.py`, lane `Real:` lines, `pi-ask` costs) and Claude subscription use (orchestrator turns, especially wake-ups for routine events; subagent runs and their models; duplicated reviews). Name the biggest spender on each meter and one change that would cut it.

Write each lesson where it will be read next time, then write the handoff and list what you changed:

- Project rules every worker needs: the repo's `CLAUDE.md`.
- Project process for orchestrators: the repo's docs (such as `docs/orchestrating.md`).
- Orchestration that applies to any repo: the skill that runs it (such as `~/Git/toolbox/skills/swarm/SKILL.md`).
- How we work together, in every repo: this file, under "Working with me".

Skip lessons already written down; edit the existing line instead of adding a near-duplicate.

End every handoff with the exact message I paste to start the next chat, in a code block: what to read (the handoff's full path) and what to do first. A bare path to the handoff is not enough.

## Working with me

- I often chat from my phone while you work: keep status updates to short bullets, lead with what changed, and give me decisions as `AskUserQuestion` picks with a recommended option first.
- Answer a message I send mid-task in your very next reply, even if it's a short "got it, doing X after Y". I shouldn't have to repeat myself.
- When I ask "are we good?" or for status, say plainly what's done, what's still running, and what needs me.
- During a run over an hour, send a one-line status about hourly, even when nothing needs me; on 2026-10-27 I had to ask after two silent hours.
- Put steps I must act on in the last message of a turn. A table written mid-turn, between tool calls, is easy to miss on my phone; I missed one on 2026-10-22.
- Before any change to the network (router, DHCP, DNS, Omada), write down the current value, the new one, and a rollback I can follow with the internet down, in the notes ledger and a home-lab runbook.
- When I report a playtest bug, ask what I saw on screen and which build I ran before theorising; on 2026-10-25 two theories were wrong because nobody asked. While I sleep, send one Pushover per finding, and a correcting one when a finding turns out wrong. Prove each playtest bug with a test that fails first.
- When I'm stuck on a website (Steamworks, a vendor dashboard), I save the page with ⌘S and give you the `.html` path. Parse it with a short `python3 -I` script for the text, links, inputs and selected options; don't Read the whole file. Walk me through one screen at a time, and say plainly when you're guessing at a screen you haven't seen. Open each screen's steps with one line on why the step exists, then short numbered clicks naming the exact button text; on 2026-10-28 "set it live on default, then beta" lost me until it said why and named the one dropdown on the row. If the file isn't there, say so and wait for me to re-save; don't fetch the same facts another way (2026-10-26).
- My machines: **moria** is the M4 Max (16 cores, 128 GB) I develop on, and Claude usually runs on it; it's dev-only, so use all its hardware. It sleeps when idle, which stalls lanes and gates (on 2026-10-21 it slept when I undocked it, despite my keep-awake app): start `caffeinate -dims -t 43200` in the background before a long run. **dungeon** is the home lab (M3 Pro, 48 GB, RAM nearly full) running services that must not be interrupted; don't put build or test load on it.
- Ask me only what needs my taste, hands, ears or money, or what can't be undone. On 2026-10-26 most of a 14-item review list didn't need me: a reviewed fix the project's own rules already favour, a "hold until X" a ticket already says, a lane-count call. Decide those, say so in the report, and keep the list to the rest.
- Before and after screenshots posted on the ticket let me judge a visual change without opening anything; do it for every visible change (2026-10-26).
- In a decision question, explain any game mechanic or term in one plain line first; I forget names (rider damage, the action cap, 2026-10-26). Write what we decide onto the tickets, not only into notes.
- Before changing something I use, find the copy I actually use. On 2026-10-26 you edited the gym HTML page while my phone ran openGym, and I synced and saw no change.
- DeepSeek credit isn't scarce: a few dollars of real balance is more than a day of work. Don't reroute work to save it; just don't waste it.

## Picking a model for delegated work

- **Always pass `model` on every `Agent` call.** A call without one inherits the orchestrator's model, usually Opus. On 2026-10-19 a research agent ran on Opus that way, and that was a miss.
- **Haiku first:** it costs far less, so use it wherever it can do the job. That covers status sweeps, running captures and gates, listing results, rebases without real conflicts, small well-specified tickets, reviews of test-only or data-only diffs, and focused read-only searches.
- **Sonnet** when the task needs judgement: design, perf work that must stay bit-identical, networking, multi-file refactors, conflict resolution, research that weighs sources, and reviews of branches with real logic. If a Haiku agent's report is thin or wrong, rerun that task on Sonnet and note it.
- **Opus** only when I ask for it.
- **Point a delegated task at the repo's own rules for it** (a command, skill or `CLAUDE.md` section) rather than restating them in the prompt. On 2026-10-21 a Haiku agent filed vault clips from my hand-written spec, never saw `.claude/commands/triage.md`, and made a string of mistakes Greg had to catch. Clip writing is Sonnet work.
- **DeepSeek** (`pi-ask.py`, `--harness pi` lanes) for every second-opinion review of a branch with logic in it, for bulk reading, and for small test-checkable tickets. Use it from the start of a session, not as an afterthought.
- **DeepSeek half price** is everything except its peak hours: 01:00–04:00 and 06:00–10:00 UTC, Monday to Friday. Weekends and Chinese public holidays are off-peak all day ([pricing](https://api-docs.deepseek.com/quick_start/pricing)). In Eastern time that is Sun–Thu 21:00–00:00 and Mon–Fri 02:00–06:00 under EDT, one hour earlier under EST (from the first Sunday of November).
- Run `deepseek-preflight.py` before starting DeepSeek work: it prints the rate now, minutes to the next peak, and the balance. Start long `pi` lanes with `--off-peak`, so they wait out peak hours. A review costs cents, so run it even at peak price.

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

Commit only your own paths: `git commit -- <paths>`. Another session may have
left files staged, and a bare `git commit` sweeps them in (two lessons, 2026-10-26).

The shell is zsh: an unquoted `$var` doesn't word-split, so
`for p in "515 01"; do set -- $p` passes one argument. Write the values out,
or use `${=p}`.
A word starting with `=` is a command lookup, so `echo ====` fails with
`=== not found` and ends a `&&` chain. Quote it (2026-10-26).

## File Inspection

Prefer the `Read`, `Grep`, and `Glob` tools over shelling out to `cat`/`head`/`tail`/`sed`/`grep` for inspecting files — they return cleaner, line-numbered, structured output and fail less. Reserve Bash for things that genuinely need it (running builds/tests, `git`, `nix`, etc.).

## Toolbox

`~/Git/toolbox` holds my dotfiles, scripts, and host configs. Its `bin/**` is on `$PATH` (recursive zsh glob), so helpers like `fetch-thread.py` work from any repo. See `~/Git/toolbox/CLAUDE.md` for details.

## LLM writing for the notes vault

Notes an LLM writes for `~/Git/notes` go in its `llm/` folder, filed with
`topics:`, never at the root. The vault's `CLAUDE.md` has the details.

## Researching Reddit

Two steps, both in `~/Git/toolbox/bin`:

1. **`reddit-search.py "<query>"`** — finds threads (`-r <sub>` repeatable to scope,
   `-s`/`-t` for sort and time window, `--format json`).
2. **`fetch-thread.py <url>`** — prints one thread's post + threaded comments.
   Works for Hacker News too.

No login, cookie or key: both go through Reddit's own `/svc/shreddit/` HTML
partials, because old.reddit.com redirects to a login page and `.json` answers 403.
`bin/fetch_reddit.py` explains the details. If they break,
`REDDIT_LIVE=1 python3 -m unittest test_fetch_reddit_live` in `toolbox/tests/`
says what Reddit changed. pi's `reddit_*` tools use the old endpoints and are
unreliable. **A 403 on moria is often only moria's IP being blocked:** run the same
command through `ssh dungeon '…'` before debugging (worked all day on 2026-10-22).

**Don't reach for `searxngr` to find Reddit threads.** It was the old workaround and
it no longer earns its place — the self-hosted instance's egress IP is blocked by
every engine that indexes Reddit deeply (DuckDuckGo and Startpage CAPTCHA, Brave
rate-limits, Google and Mojeek return nothing). For general web search it still works:
Bing and Yahoo answer, and on 2026-10-18 it beat DeepSeek Search on dev queries
(`~/Git/home-lab/docs/llm-gateway.md`). `WebSearch` is the fallback.

## Agent skills

### Writing a skill or an agent tool

Follow `~/Git/toolbox/skills/README.md`: one skill set for Claude Code, pi and
Hermes, with the tool itself a script in `~/Git/toolbox/bin/`.

### Issue tracker

Wayfinder, to-spec and to-tickets need to know where this repo tracks issues.
Run `git config wayfinder.tracker`. `github` means GitHub Issues: follow
`~/.claude/skills/setup-matt-pocock-skills/issue-tracker-github.md`. `local` means
markdown files under `.scratch/`: follow
`~/.claude/skills/setup-matt-pocock-skills/issue-tracker-local.md`. If it is unset,
ask the user which of the two this repo should use, then store the answer with
`git config wayfinder.tracker <answer>` before doing anything else. A repo's own
CLAUDE.md issue-tracker block overrides this. If a label a skill applies does not
exist yet, `gh label create` it first.

The choice lives in local git config on purpose: never committed, so a work repo's
history stays clean, and shared by every worktree of the clone.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the repo root. Follow
`~/.claude/skills/setup-matt-pocock-skills/domain.md`.
