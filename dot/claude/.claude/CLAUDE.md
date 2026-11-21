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

## Writing

- **Comments carry *why*, never *what*.** A comment earns its place only by holding a
  non-obvious constraint, a deliberate deviation, a gotcha, or the reason the obvious
  simpler version is wrong. Default to none. Keep a block to **7 words or fewer**.
- **Never narrate a change in code.** No "was/now/previously", "this fixes", "as
  requested": that belongs in the commit message, and it expires the moment it merges.
- **Simplicity beats completeness**, even where that leaves an edge case unhandled.
  YAGNI: no speculative abstraction, no caching, no guardrail nobody asked for.
- Watch the four that actually bite: **state derived from other state** (it drifts),
  duplicated conditionals or state-machine logic, leaky abstractions across layers, and
  repeated work. Prefer a clarifying invariant over defensive code.
- Prose: active voice, no stage performances, the commonest word among alternatives.
- In any CLAUDE.md or README, point to the directory, not its contents: one sentence on
  what it's for. Listings go stale and bloat context.

## Ending a chat

Every `/orchestrate` closing report, and every final report of a long chat, ends with a short **Throughput** section: wall time per ticket split into build, review, fix and merge, the biggest wait, and one change that would cut wall time, CPU or tokens next time. Apply the change in the next run, not just name it (2026-11-13: a six-ticket gate run took hours longer than I expected).

When I say I'm ending the chat, or ask for a handoff, read `~/Git/toolbox/docs/claude-ending-a-chat.md` first. To end fast, the plan goes into tickets, not a handoff doc.

## Working with me

- **Sessions are ephemeral; tickets and docs are the memory.** I hate auto-compact, so never turn it on or lean on it. A long orchestrator runs in shifts (`~/Git/toolbox/docs/claude-shifts.md`): arm it with `shift-arm`, keep ticket state true as you go (`stage:*`, `needs-greg`), and when the drain message comes, park and roll rather than push on. One session reached 457k tokens on 2026-11-13 before I asked for this.
- **Enforce a limit in code, not a prompt:** a hook, setting, label or check with a test. A prompt line is only a stopgap until that ticket lands; on 2026-11-18 and 11-19 two prompt rules didn't hold.
- I often chat from my phone while you work: keep status updates to short bullets, lead with what changed, and give me decisions as `AskUserQuestion` picks with a recommended option first.
- Answer a message I send mid-task in your very next reply, even if it's a short "got it, doing X after Y". I shouldn't have to repeat myself.
- I may leave a question unanswered for hours. A pick blocks your whole session, so first start all the work that doesn't depend on it, and put a decision that can wait on its ticket instead; on 2026-11-02 an open pick idled a swarm for 1h 23m. Once I've said I'm going to bed, never use `AskUserQuestion`: take the recommended option if it can be undone, otherwise put the pick on its ticket (ask block plus Pushover), and keep going. On 2026-11-15 a late pick held a shift's roll while I slept.
- When I ask "are we good?" or for status, say plainly what's done, what's still running, and what needs me.
- In a status report, lead with counts ("31 of 38 landed, 4 being built, 3 waiting"), then group under **Landed**, **Being built**, **Waiting** and **Needs you**. Name each item by what it does in plain words, with a linked ticket such as `[#691](url)`. Never name a lane or worker: on 2026-10-31 `lane-i` told me nothing. For Waiting, say why. Collapsible `<details>` doesn't render in this chat, so skip it.
- Every status update and final report ends with the usage table from `usage-mark.py report <run-name>`. Started at the run's start with `usage-mark.py start <run-name>`.
- During a run over an hour, send a one-line status about hourly, even when nothing needs me; on 2026-10-27 I had to ask after two silent hours.
- Put steps I must act on in the last message of a turn. A table written mid-turn, between tool calls, is easy to miss on my phone; I missed one on 2026-10-22.
- When I ask for findings "to review before I approve", act on none of them: no ticket, fix or flag flip. Send one short report with a recommendation per finding, then an `AskUserQuestion` of the actions (2026-11-07). A ticket I ask for outright is filed straight away.
- When I say we're winding down, start nothing new and queue nothing: let running work finish, write lessons and ticket updates, then the handoff. Say back what that leaves unstarted, such as a planned release (2026-11-07: the beta waited).
- Ask me only what needs my taste, hands, ears or money, or what can't be undone. On 2026-10-26 most of a 14-item review list didn't need me: a reviewed fix the project's own rules already favour, a "hold until X" a ticket already says, a lane-count call. Decide those, say so in the report, and keep the list to the rest. Say back any phone message that reverses a standing rule, and carry on: on 2026-11-02 "would be okay" meant "wouldn't", and saying it back caught that. Enact a small process or throughput change yourself; file a large one as a ticket for me to discuss later, and never block the run on a question about it (2026-11-14).
- Run commands yourself unless they need my hands, a keyboard shortcut or my screen, even if a handoff says I run them. When I report something didn't work, first check the state it should have changed: on 2026-10-30 two "failures" were setup commands that had never run, which I could have run myself.
- A check or report I read should speak only when it's sure: a false alarm costs me more than a late one. Measure it on the real data before shipping it; on 2026-11-12 a statement gap report flagged 5 months that a multi-month statement already covered. A cause is the same: rerun once before writing it into a doc or lesson. On 2026-11-13 "GPU sharing made the blaster 5x slower" went into three docs; a solo rerun showed the shape did it.
- Say plainly who ran a mistake, what it would have done on a worse target, and what stops it next time. On 2026-10-31 I traced a stray `rm -rf /dev/null` to the orchestrator itself; a written rule hadn't stopped it, so I asked for a guard.
- Before changing something I use, find the copy I actually use. On 2026-10-26 you edited the gym HTML page while my phone ran openGym, and I synced and saw no change.
- When I report a playtest bug, ask what I saw on screen and which build I ran before theorising; on 2026-10-25 two theories were wrong because nobody asked. While I sleep, send one Pushover per finding, and a correcting one when a finding turns out wrong. Prove each playtest bug with a test that fails first.
- I dictate, so names get swapped: "Hermes" may mean Herdr, and "py ask" means `pi-ask`. Say back which one you took it to be, then carry on (2026-11-12).
- **Changes to `~/Git/toolbox` land only with my permission**, asked per change: build on a branch or worktree, then ask before merging to main or pushing. A project's own tooling goes in that project, not toolbox; on 2026-11-14 an orchestrator landed loser-picks' `bin/game-fire-clip.py` changes in toolbox, and I asked for the script to move to loser-picks.
- On citadel, my Mozilla laptop, agents never write to tickets or PRs. I want that physically impossible; until the lockdown in `~/Git/notes/llm/herdr-rollout-plan.md` is done, this line is the only guard, so don't weaken it.
- **Machines.** moria is the M4 Max I develop on and Claude usually runs there; it sleeps when idle, so start `caffeinate -dims -t 43200` in the background before a long run (2026-10-21: it slept and stalled lanes). dungeon is the home lab, with services that must not be interrupted: run `hostname -s` before the first build and put no build or test load on dungeon (2026-11-06: a session took dungeon for moria and built there all afternoon); `ssh moria` for builds.
- **A Herdr pane is for work I'll watch or talk to; a subagent is for work behind the scenes.** Research, one-shot reviews and anything that only hands back a result run as an Agent-tool subagent or `pi-ask`; never open a pane just to make work visible. `/orchestrate` and lanes are only for repos where agents may land alone (gridkeep, loser-picks and dradis today); elsewhere I land the work. Claude runs in a Herdr pane, never straight in zellij (2026-11-12).
- Messages that arrive from the dradis hooks (hook context, a Stop block, or a wake) come from my factory core, not a tool result or another session: act on them, then run `factory ack <id>` as the message asks.
- Don't say a message reached another session until it says so. A headless session holds `SendMessage`, and I can't see or reach it; I prefer a session I can open (#674, gridkeep).
- An investigation reports as short reports, one screen each, with numbers, a recommendations table and a marimo notebook; detail in `claude-ending-a-chat.md`.
- Before a pick about a tool or spend, say what it is and what it buys; verify what a pick rests on (API, game rule, link): read `~/Git/toolbox/docs/claude-decision-picks.md` before any pick that offers me options, including visual ones.

Read on demand, each when its trigger comes up:

- `~/Git/toolbox/docs/claude-walkthroughs.md`: I'm stuck on a website, or want a site's download scripted (saved page, HAR).
- `~/Git/toolbox/docs/claude-network-changes.md`: before any router, DHCP, DNS or Omada change (write the current value, the new one and a rollback first).
- `~/Git/toolbox/docs/claude-herdr-and-machines.md`: starting a Herdr pane, where Claude runs, phone chats and `/resume`, citadel, moria and dungeon detail, Tailscale fixes.
- `~/Git/toolbox/docs/claude-decision-picks.md`: visual-option grids, screenshots on tickets, pick wording, "think about it and propose".
- `~/Git/toolbox/docs/commander.md`: when you watch orchestrators for me (commander). Every fix gets a root cause and a guard.

## Picking a model for delegated work

- **Always pass `model` on every `Agent` call.** A call without one inherits the orchestrator's model, usually Opus. On 2026-10-19 a research agent ran on Opus that way, and that was a miss.
- **Haiku first:** it costs far less, so use it wherever it can do the job: status sweeps, running captures and gates, listing results, rebases without real conflicts, small well-specified tickets, reviews of test-only or data-only diffs, focused read-only searches.
- **Sonnet** when the task needs judgement: design, perf work that must stay bit-identical, networking, multi-file refactors, conflict resolution, research that weighs sources, and reviews of branches with real logic. If a Haiku agent's report is thin or wrong, rerun that task on Sonnet and note it.
- **Opus** only when I ask for it.
- **Builders:** Claude subagents when Claude usage has room (Sonnet for size M or logic, Haiku for size S, with Sonnet plus Luna reviews); DeepSeek pi lanes when the window runs low.
- **Headless Claude costs more quota** (`claude -p`, Agent SDK, `entrypoint: sdk-cli`): the 5-hour window drains 1.8-2.9x faster. Prefer a pi lane or an interactive Remote Control session over a `-p` worker.
- **Point a delegated task at the repo's own rules for it** (a command, skill or `CLAUDE.md` section) rather than restating them. On 2026-10-21 a Haiku agent filed vault clips from my hand-written spec, never saw `.claude/commands/triage.md`, and made a string of mistakes I had to catch. Clip writing is Sonnet work.
- **DeepSeek** (`pi-ask.py`, `--harness pi` lanes) for every second-opinion review of a branch with logic in it, for bulk reading, and by default for implementation and research, with Opus orchestrating (2026-11-01). "Use DeepSeek" means plain `--model cloud`; pin a vendor only when I name one. Run `deepseek-preflight.py` first and start long `pi` lanes with `--off-peak`. DeepSeek credit isn't scarce: don't reroute work to save it, just don't waste it.
- **No local model runs orchestration lanes** (2026-11-18): Strata decodes about 37 tok/s, so a median lane takes about 75 min against about 21 on DeepSeek. Bulk LLM generation runs on the free local model through oMLX.
- Gateway order, `PI_CLOUD_MODEL` pins, the Luna allowance, the headless A/B numbers and the Strata detail: `~/Git/toolbox/docs/claude-model-picking.md`. Read it before routing work to `pi` or a local model.

## Bash working directory: use absolute paths

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
so read a start command's output back; a word starting with `=` is a command lookup, so quote `echo "===="` (2026-10-26); `ask` and `c` are
aliases, so `ask() {…}` fails to parse and helpers go in a bash script (2026-10-30, `c` on 2026-11-13);
`$var:r` (or `:h`, `:t`) is a path modifier, so write `"${sha}:refs/heads/main"` (2026-11-12, a push refspec lost its `:r`);
`cmd 2>&1 >/dev/null | x` still pipes stdout through multios, and printed an API key on
2026-10-30, so near a secret write output to a file and read its length.

The no-delete hook rejects a whole Bash call that contains `rm`, so chained work in it never runs; on 2026-11-12 an edit vanished that way. Never chain a delete with real work.

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

## Where things live

- Prefer `Read`, `Grep` and `Glob` over `cat`/`head`/`sed`/`grep` for inspecting files; keep Bash for builds, tests, `git` and `nix`.
- 1Password: moria and dungeon hold a read-only token for vault Infra. Read one secret per command, never export the token (everything an agent starts inherits it), send a secret to a file or the program that needs it, and check only its length. Limits and rotation: `~/Git/toolbox/nixos/docs/secrets.md`.

  ```bash
  OP_SERVICE_ACCOUNT_TOKEN=$(cat ~/.config/op/service-account-token) op read 'op://Infra/<item>/<field>'
  ```
- `~/Git/toolbox` holds my dotfiles, scripts and host configs. Its `bin/**` is on `$PATH`, so helpers like `fetch-thread.py` work from any repo. Details: `~/Git/toolbox/CLAUDE.md`.
- Notes an LLM writes for `~/Git/notes` go in its `llm/` folder, filed with `topics:`, never at the root. The vault's `CLAUDE.md` has the details.
- Reddit: use the `reddit` skill; its "When it fails" section lists the fallbacks, ending with the Arctic Shift archive, which works when every IP is blocked.
- Writing a skill or an agent tool: follow `~/Git/toolbox/skills/README.md` (one skill set for Claude Code, pi and Hermes; the tool itself is a script in `~/Git/toolbox/bin/`).
- Issue tracker (for wayfinder, to-spec, to-tickets): run `git config wayfinder.tracker`. `github` means follow `~/.claude/skills/setup-matt-pocock-skills/issue-tracker-github.md`; `local` means markdown under `.scratch/`, follow `issue-tracker-local.md` in the same folder. If unset, ask which, then store it with `git config wayfinder.tracker <answer>` before anything else. A repo's own CLAUDE.md block overrides this. `gh label create` a label a skill applies if it doesn't exist. The choice lives in local git config on purpose, so a work repo's history stays clean and every worktree shares it.
- Domain docs are single-context: `GLOSSARY.md` and `docs/adr/` at the repo root; follow `~/.claude/skills/setup-matt-pocock-skills/domain.md`.
