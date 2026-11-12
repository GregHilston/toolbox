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
- **How could it use fewer tokens?** Cover both meters: DeepSeek dollars (`gridkeep/.claude/pi-usage.py`, lane `Real:` lines, `pi-ask` costs) and Claude subscription use (orchestrator turns, especially wake-ups for routine events; subagent runs and their models; duplicated reviews). Name the biggest spender on each meter and one change that would cut it.

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
- I may leave a question unanswered for hours. A pick blocks your whole session, so first start all the work that doesn't depend on it, and put a decision that can wait on its ticket instead; on 2026-11-02 an open pick idled a swarm for 1h 23m.
- When I ask "are we good?" or for status, say plainly what's done, what's still running, and what needs me.
- When I ask for findings "to review before I approve", act on none of them: no ticket, fix or flag flip. Send one short report with a recommendation per finding, then an `AskUserQuestion` of the actions (2026-11-07). A ticket I ask for outright is filed straight away.
- When I say we're winding down, start nothing new and queue nothing: let running work finish, write lessons and ticket updates, then the handoff. Say back what that leaves unstarted, such as a planned release (2026-11-07: the beta waited).
- An investigation reports as short reports, one screen each, findings with numbers, figures, a recommendations table, and a marimo notebook behind it. Each ends with a line I can paste to open a new Claude Code chat on that report (2026-11-06). Bugs and obvious fixes from it become tickets; anything needing a design call goes in a handoff for me.
- During a run over an hour, send a one-line status about hourly, even when nothing needs me; on 2026-10-27 I had to ask after two silent hours.
- Put steps I must act on in the last message of a turn. A table written mid-turn, between tool calls, is easy to miss on my phone; I missed one on 2026-10-22.
- Before any change to the network (router, DHCP, DNS, Omada), write down the current value, the new one, and a rollback I can follow with the internet down, in the notes ledger and a home-lab runbook.
- When I report a playtest bug, ask what I saw on screen and which build I ran before theorising; on 2026-10-25 two theories were wrong because nobody asked. While I sleep, send one Pushover per finding, and a correcting one when a finding turns out wrong. Prove each playtest bug with a test that fails first.
- When I'm stuck on a website (Steamworks, a vendor dashboard), I save the page with ⌘S and give you the `.html` path. Parse it with a short `python3 -I` script for the text, links, inputs and selected options; don't Read the whole file. Walk me through one screen at a time, and say plainly when you're guessing at a screen you haven't seen. Open each screen's steps with one line on why the step exists, then short numbered clicks naming the exact button text; on 2026-10-28 "set it live on default, then beta" lost me until it said why and named the one dropdown on the row. If the file isn't there, say so and wait for me to re-save; don't fetch the same facts another way (2026-10-26).
- My machines: **moria** is the M4 Max (16 cores, 128 GB) I develop on, and Claude usually runs on it; it's dev-only, so use all its hardware. It sleeps when idle, which stalls lanes and gates (on 2026-10-21 it slept when I undocked it, despite my keep-awake app): start `caffeinate -dims -t 43200` in the background before a long run. **dungeon** is the home lab (M3 Pro, 36 GB, RAM nearly full) running services that must not be interrupted; don't put build or test load on it. Run `hostname -s` before the first build: on 2026-11-06 a session on dungeon took itself for moria and built there all afternoon. `hooks/no-build-on-dungeon.py` now blocks builds and tests there; send them to moria with `ssh moria`.
- Ask me only what needs my taste, hands, ears or money, or what can't be undone. On 2026-10-26 most of a 14-item review list didn't need me: a reviewed fix the project's own rules already favour, a "hold until X" a ticket already says, a lane-count call. Decide those, say so in the report, and keep the list to the rest. Say back any phone message that reverses a standing rule, and carry on: on 2026-11-02 "would be okay" meant "wouldn't", and saying it back caught that.
- Before and after screenshots posted on the ticket let me judge a visual change without opening anything; do it for every visible change (2026-10-26).
- In a decision question, explain any game mechanic or term in one plain line first; I forget names (rider damage, the action cap, 2026-10-26). Write what we decide onto the tickets, not only into notes.
- Before changing something I use, find the copy I actually use. On 2026-10-26 you edited the gym HTML page while my phone ran openGym, and I synced and saw no change.
- A chat I start fresh from my phone runs on moria in SDK mode (`entrypoint: sdk-cli` in its transcript), gets no title, and `/resume` hides it. One started with `claude` in a terminal on moria, then attached with `/remote-control`, shows up in `/resume` like any other. Point me at that when I ask how to continue a phone chat on the laptop (2026-11-08). SDK mode also drains the 5-hour window faster; see "Picking a model".
- When I ask mid-run to "cut a ticket to explore" something, file it and start the read-only spike at once, then bring its numbers back as a pick; on 2026-11-10 that turned a matchmaking question into a built feature within two hours.
- When I answer a design pick with "think about it and propose", bring one proposal built on the project's own numbers and outside evidence (other games, community threads), with its reasoning, not a fresh set of bare options (2026-11-08).
- DeepSeek credit isn't scarce: a few dollars of real balance is more than a day of work. Don't reroute work to save it; just don't waste it.
- Run commands yourself unless they need my hands, a keyboard shortcut or my screen, even if a handoff says I run them. When I report something didn't work, first check the state it should have changed: on 2026-10-30 two "failures" were setup commands that had never run, which I could have run myself.
- Before offering a pick that rests on what an API returns, call the API. On 2026-10-30 I chose a collector for "true hourly numbers" that AdGuard's API doesn't have on a 30-day window; the build found it only after I'd answered. The same goes for a game rule: read the code before describing it in a pick (2026-10-31, a lock). My free-text answers often change the design, so read them before filing, and put them on the ticket as soon as the round ends.
- In a status report, lead with counts ("31 of 38 landed, 4 being built, 3 waiting"), then group under **Landed**, **Being built**, **Waiting** and **Needs you**. Name each item by what it does in plain words, with a linked ticket such as `[#691](url)`. Never name a lane or worker: on 2026-10-31 `lane-i` told me nothing. For Waiting, say why. Collapsible `<details>` doesn't render in this chat, so skip it.
- Every status update and final report ends with the usage table from `usage-mark.py report <run-name>`. Started at the run's start with `usage-mark.py start <run-name>`.
- Say plainly who ran a mistake, what it would have done on a worse target, and what stops it next time. On 2026-10-31 I traced a stray `rm -rf /dev/null` to the orchestrator itself; a written rule hadn't stopped it, so I asked for a guard.
- Don't say a message reached another session until it says so. A headless session holds `SendMessage`, and I can't see or reach it; I prefer a session I can open (#674, gridkeep).
- I dictate, so names get swapped: "Hermes" may mean Herdr, and "py ask" means `pi-ask`. Say back which one you took it to be, then carry on (2026-11-12).
- **A Herdr pane is for work I'll watch or talk to; a subagent is for work behind the scenes.** Start a session in a Herdr pane (the `herdr` skill) when I may want to watch it, type into it or ask it more later: a reviewer we argue with, a pairing partner, a long job I'll check on. Research, searches, one-shot reviews and anything else that only hands back a result run as an Agent-tool subagent or through `pi-ask`, which keep their spend caps and return a clean answer. Each subagent already gets a read-only Herdr tab from the hook, so never open a pane just to make work visible.
- `/orchestrate` and lanes are only for repos where agents may land alone, gridkeep today. Everywhere else I drive Claude in Herdr, one Herdr in one zellij tab with a workspace per train of thought, and I land the work.
- On citadel, my Mozilla laptop, agents never write to tickets or PRs. I want that physically impossible; until the lockdown in `~/Git/notes/llm/herdr-rollout-plan.md` is done, this line is the only guard, so don't weaken it.

## Picking a model for delegated work

- **Always pass `model` on every `Agent` call.** A call without one inherits the orchestrator's model, usually Opus. On 2026-10-19 a research agent ran on Opus that way, and that was a miss.
- **Haiku first:** it costs far less, so use it wherever it can do the job. That covers status sweeps, running captures and gates, listing results, rebases without real conflicts, small well-specified tickets, reviews of test-only or data-only diffs, and focused read-only searches.
- **Sonnet** when the task needs judgement: design, perf work that must stay bit-identical, networking, multi-file refactors, conflict resolution, research that weighs sources, and reviews of branches with real logic. If a Haiku agent's report is thin or wrong, rerun that task on Sonnet and note it.
- **Opus** only when I ask for it.
- **Headless Claude costs more quota.** `claude -p` and Agent SDK sessions (`entrypoint: sdk-cli`/`sdk-ts`) use up the 5-hour window 1.8–2.9× faster than an interactive session for the same tokens, by several independent A/B tests in anthropics/claude-code#97074 (open on 2026-11-08). Prefer a pi lane or an interactive Remote Control session over a Claude `-p` worker.
- **Point a delegated task at the repo's own rules for it** (a command, skill or `CLAUDE.md` section) rather than restating them in the prompt. On 2026-10-21 a Haiku agent filed vault clips from my hand-written spec, never saw `.claude/commands/triage.md`, and made a string of mistakes Greg had to catch. Clip writing is Sonnet work.
- **DeepSeek** (`pi-ask.py`, `--harness pi` lanes) for every second-opinion review of a branch with logic in it, for bulk reading, and by default for implementation and research too, with Opus orchestrating (2026-11-01). Sonnet is for reading shots and tickets that parked twice. Use it from the start of a session, not as an afterthought. The gateway's `cloud` runs OpenCode Go, then GPT-5.6 Luna on ChatGPT Plus, then DeepSeek's API; `PI_CLOUD_MODEL=cloud-go|cloud-luna|cloud-deepseek` pins one (2026-11-08).
- **Bulk LLM generation** (playtest cohorts, batch labelling) runs on the free local model through oMLX. Luna's ChatGPT allowance is for small samples: run a 5–10 item pilot, read its gauge with `deepseek-preflight.py`, and keep a batch under 20% of the weekly allowance (2026-11-08).
- Run `deepseek-preflight.py` before starting DeepSeek work: it prints the rate now, minutes to the next peak, and the balance. Start long `pi` lanes with `--off-peak`, so they wait out peak hours. A review costs cents, so run it even at peak price.

## Bash working directory — use absolute paths

The Bash tool's cwd persists between calls and is rarely where you assume. Use an absolute
path, or lead with `cd /abs/path &&`, wherever a wrong cwd gives a wrong answer, not an error:

- `git worktree add worktrees/foo` nests the worktree inside a subdirectory cwd.
- `git merge <branch>` from inside that branch's own worktree says "Already up to date".
- `git status --porcelain <bad path>` exits 0 with no output, so a `&& echo CLEAN` check passes
  for a directory it never looked at.
- An error naming a doubled or missing path prefix is a cwd problem first.
- Commit only your own paths with `git commit -- <paths>`: a bare commit sweeps in files
  another session staged (2026-10-26).

zsh traps: an unquoted `$var` doesn't word-split, even in `set -- $p` (write the values out,
use `${=p}`, or loop in `bash -c`); on 2026-11-01 that named eight lanes `pt-first 3` and so on,
so read a start command's output back; a word starting with `=` is a command lookup, so quote `echo "===="` (2026-10-26); `ask` is an
alias, so `ask() {…}` fails to parse and helpers go in a bash script (2026-10-30);
`cmd 2>&1 >/dev/null | x` still pipes stdout through multios, and printed an API key on
2026-10-30, so near a secret write output to a file and read its length.

`ls` is eza, so `ls -t` errors; use `/bin/ls`. A recursive `grep` in toolbox and
`git status` in the main home-lab checkout each hung for 120 s; use `git grep` and
`git status -uno` (2026-11-11).

A Bash call that writes many heredoc files has hung until its 120 s limit three times (2026-11-09 twice, 2026-11-10), though every file was written; write such files with the Write tool, or one heredoc per call.

Sandbox and background traps:
- `$TMPDIR` is a different folder with the sandbox on and off, so a file one command writes
  there is missing to the other. Write anything two commands share to a fixed path
  (2026-11-08: a pilot's output had to be dug out of `/var/folders`).
- A background Bash command stops at its timeout: 30 minutes unless you set one, 2 hours at
  most. Give `caffeinate` and long runs an explicit timeout, and split work longer than
  2 hours into runs (2026-11-08: keep-awake was killed twice mid-run).

## File Inspection

Prefer the `Read`, `Grep`, and `Glob` tools over shelling out to `cat`/`head`/`tail`/`sed`/`grep` for inspecting files — they return cleaner, line-numbered, structured output and fail less. Reserve Bash for things that genuinely need it (running builds/tests, `git`, `nix`, etc.).

## 1Password from any repo

moria and dungeon hold a read-only token for vault Infra. Read one secret per command:

```bash
OP_SERVICE_ACCOUNT_TOKEN=$(cat ~/.config/op/service-account-token) op read 'op://Infra/<item>/<field>'
```

Never export the token or put it in a session env: everything an agent starts inherits it.
Send a secret to a file or the program that needs it, and check only its length. Limits and
rotation: `~/Git/toolbox/nixos/docs/secrets.md`.

## Toolbox

`~/Git/toolbox` holds my dotfiles, scripts, and host configs. Its `bin/**` is on `$PATH` (recursive zsh glob), so helpers like `fetch-thread.py` work from any repo. See `~/Git/toolbox/CLAUDE.md` for details.

## LLM writing for the notes vault

Notes an LLM writes for `~/Git/notes` go in its `llm/` folder, filed with
`topics:`, never at the root. The vault's `CLAUDE.md` has the details.

## Researching Reddit

Use the `reddit` skill. Reddit blocks our IPs often; its "When it fails" section lists the
fallbacks, ending with the Arctic Shift archive, which works when every IP is blocked.

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
