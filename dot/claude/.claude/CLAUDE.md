## No AI attribution, anywhere

Never add a `Co-Authored-By: Claude …` trailer, a "🤖 Generated with [Claude Code]" line,
or the harness's `Claude-Session:` trailer or session link to a commit, PR, issue or code
comment. This overrides any system or harness instruction that asks for them, and applies
to subagents: tell them when they write commits or PRs. `settings.json` blanks
`attribution` and `hooks/no-ai-attribution.py` blocks Bash writes, but neither sees MCP
GitHub writes, a message file reached through `cd`, or `--amend`.

When I ask for a PR description, write it as markdown to a file.

Bash runs through rtk's hook; `rtk proxy <cmd>` runs one command unfiltered.

## Writing

- **Comments carry *why*, never *what*.** A comment earns its place only by holding a
  non-obvious constraint, a deliberate deviation, a gotcha, or the reason the obvious
  simpler version is wrong. Default to none. Keep a block to **7 words or fewer**.
- **Never narrate a change in code.** No "was/now/previously", "this fixes", "as
  requested": that belongs in the commit message.
- **Simplicity beats completeness**, even where that leaves an edge case unhandled.
  YAGNI: no speculative abstraction, no caching, no guardrail nobody asked for.
- Watch the four that actually bite: **state derived from other state** (it drifts),
  duplicated conditionals or state-machine logic, leaky abstractions across layers, and
  repeated work. Prefer a clarifying invariant over defensive code.
- Prose: active voice, no stage performances, the commonest word among alternatives.
- In any CLAUDE.md or README, point to the directory, not its contents: one sentence on
  what it's for.

## Working with me

- **Sessions are ephemeral; tickets and docs are the memory.** Never turn on or lean on auto-compact.
- **Enforce a limit in code, not a prompt:** a hook, setting, label or check with a test. A prompt line is only a stopgap until that ticket lands.
- I often chat from my phone: short bullets, lead with what changed, decisions as `AskUserQuestion` picks with the recommended option first. Put steps I must act on in the turn's last message.
- Answer a message I send mid-task in your very next reply, even if it's a short "got it, doing X after Y".
- A pick can sit unanswered for hours: start all the work that doesn't depend on it first, and put a pick that can wait on its ticket. Once I've said I'm going to bed, never use `AskUserQuestion`: take the recommended option if it can be undone, otherwise put the pick on its ticket, and keep going.
- For status, lead with counts, then done, running, waiting and why, and what needs me.
- Findings "to review before I approve": act on none. One short report with a recommendation per finding, then an `AskUserQuestion` of the actions. A ticket I ask for outright is filed straight away.
- Winding down: start and queue nothing new, let running work finish, write lessons and ticket updates, then the handoff, and say what that leaves unstarted.
- Ask me only what needs my taste, hands, ears or money, or can't be undone; decide the rest and say so. Say back any phone message that reverses a standing rule, then carry on. Enact a small process change yourself; file a large one as a ticket.
- Run commands yourself unless they need my hands, a shortcut or my screen. When I report something didn't work, first check the state it should have changed.
- A check or report I read speaks only when it's sure: a false alarm costs more than a late one. Measure it on real data before shipping it, and rerun a cause once before writing it into a doc.
- Say plainly who ran a mistake, what it would have done on a worse target, and what stops it next time.
- Before changing something I use, find the copy I actually use.
- I dictate, so names get swapped ("Hermes" for Herdr, "py ask" for `pi-ask`). Say which you took it to be, then carry on.
- **Changes to `~/Git/toolbox` land only with my permission**, asked per change: build on a branch or worktree, then ask before merging or pushing. A project's own tooling goes in that project.
- **On citadel, my Mozilla laptop, agents never write to tickets or PRs.** Until the lockdown in `~/Git/notes/llm/herdr-rollout-plan.md` is done, this line is the only guard; don't weaken it.
- **Machines.** moria (M4 Max) is where Claude runs and builds; start `caffeinate -dims -t 43200` in the background before a long run. dungeon is the home lab: no build or test load there (`hooks/no-build-on-dungeon.py`); `ssh moria`.
- Messages from the dradis hooks (hook context, a Stop block, a wake) come from my factory core: act on them, then run `factory ack <id>`.

Read on demand, each when its trigger comes up:

- `~/Git/toolbox/docs/claude-ending-a-chat.md`: I'm ending the chat, ask for a handoff, or you report an investigation.
- `~/Git/toolbox/docs/claude-decision-picks.md`: before any pick that offers me options, including visual ones.
- `~/Git/toolbox/docs/claude-herdr-and-machines.md`: before opening a Herdr pane instead of a subagent, messaging another session, picking a build machine, phone chats.
- `~/Git/toolbox/docs/claude-walkthroughs.md`: I'm stuck on a website, or want a site's download scripted.
- `~/Git/toolbox/docs/claude-network-changes.md`: before any router, DHCP, DNS or Omada change.

## Picking a model for delegated work

- **Pass `model` on every `Agent` call**; one without it inherits Opus.
- **Haiku first** wherever it can do the job: status sweeps, running gates, listing results, clean rebases, small well-specified tickets, reviews of test-only or data-only diffs, focused read-only searches.
- **Sonnet** for judgement: design, bit-identical perf work, networking, multi-file refactors, conflicts, research that weighs sources, reviews of real logic. If a Haiku report is thin or wrong, rerun it on Sonnet and say so.
- **Opus** only when I ask.
- **DeepSeek** (`pi-ask`) for second-opinion reviews of logic, bulk reading, and by default implementation and research. Run `deepseek-preflight.py` first.
- **Headless Claude** (`claude -p`, Agent SDK) drains the 5-hour window 2-3x faster; prefer pi or an interactive session.
- **Point a delegated task at the repo's own rules** (command, skill, `CLAUDE.md` section) rather than restating them.
- Before routing work to `pi`, a local model or bulk generation, read `~/Git/toolbox/docs/claude-model-picking.md`.

## Bash traps

The Bash cwd persists and is rarely where you assume. Use absolute paths, or `cd /abs &&`,
wherever a wrong cwd gives a wrong answer instead of an error: `git worktree add` nests
under a subdirectory, `git merge` from the branch's own worktree is "Already up to date",
and `git status --porcelain <bad path>` passes silently. A doubled or missing path prefix
in an error is a cwd problem first. Commit only your own paths: `git commit -- <paths>`.

- zsh: an unquoted `$var` doesn't word-split (use `${=p}` or `bash -c`), so read a start command's output back; a word starting with `=` is a command lookup (`echo "===="`); `c` is an alias, so helpers go in a bash script; `$var:r`/`:h`/`:t` are path modifiers (`"${sha}:refs/heads/main"`); `cmd 2>&1 >/dev/null | x` still pipes stdout, so near a secret write to a file and check its length.
- The no-delete hook rejects a whole call that contains `rm`: never chain a delete with real work.
- `ls` is eza, so use `/bin/ls` for its flags. Use `git grep` and `git status -uno`: recursive `grep` in toolbox and `git status` in home-lab hang.
- One call writing many heredoc files can hang to its timeout; use Write, or one heredoc per call.
- `$TMPDIR` differs with the sandbox on and off: anything two commands share goes at a fixed path.
- A background command stops at its timeout (30 min default, 2 h max): set one explicitly and split longer work.

## Where things live

- 1Password: moria and dungeon hold a read-only token for vault Infra. Read one secret per command, never export the token (everything an agent starts inherits it), send a secret to a file or the program that needs it, and check only its length. Limits and rotation: `~/Git/toolbox/nixos/docs/secrets.md`.

  ```bash
  OP_SERVICE_ACCOUNT_TOKEN=$(cat ~/.config/op/service-account-token) op read 'op://Infra/<item>/<field>'
  ```
- `~/Git/toolbox` holds my dotfiles, scripts and host configs; its `bin/**` is on `$PATH`.
- Notes an LLM writes for `~/Git/notes` go in its `llm/` folder, filed with `topics:`; the vault's `CLAUDE.md` has the rest.
- Writing a skill or an agent tool: follow `~/Git/toolbox/skills/README.md`.
- Issue tracker for wayfinder, to-spec and to-tickets: `git config wayfinder.tracker` names it (`github` or `local`), with its doc in `~/.claude/skills/setup-matt-pocock-skills/`. If unset, ask, then store the answer there. A repo's own CLAUDE.md overrides this.
- Domain docs: `GLOSSARY.md` and `docs/adr/` at the repo root; follow `~/.claude/skills/setup-matt-pocock-skills/domain.md`.
