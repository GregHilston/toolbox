---
name: lab-service
description: Add one or more services to the home lab. Research each with subagents, pitch a design per group for Greg's sign-off, then commit, deploy to dungeon and verify every touchpoint (Caddy, Homepage, probe, alerts, backups, docs). Use for /lab-service.
disable-model-invocation: true
argument-hint: "<service> [<service>…] [deploy]"
---

# lab-service

You are the orchestrator. Subagents research and write; you hold the checklist, talk to
Greg, and own the commits. **Pitch mode** is the default: nothing changes on dungeon until
Greg signs off on a group. With the word `deploy` in the arguments, skip sign-off and go
straight from research to deploy, but still show each pitch.

The checklist lives in the lab repo, not here:
`~/Git/home-lab/docs/adding-a-service.md`. Read it and `~/Git/home-lab/CLAUDE.md` before
step 1. Its touchpoint table is the bar for every step below.

## 1. Group, then interview

Split the request into **groups**: a service plus whatever ships only with it (paperless and
its Postgres, Redis and Tika are one group; a sync tool that feeds it is another). One
group becomes one pitch and one commit.

Look before you ask: `ssh unraid ls /mnt/user/` for existing shares and data,
the compose file for clashes, and any old copy of the service. Then ask Greg **one**
`AskUserQuestion` round (at most 4 questions, recommended option first), covering only
what changes the design: privacy (which LLM alias sees the data: `local-lab` keeps it in
the house), what must never break (a DNS service must fail open), where existing data
lives, and scope. **Done when** each group has a goal, its constraints and its client test,
meaning the thing Greg will do on a phone or laptop to call it working.

## 2. Research, one Sonnet agent per group, in parallel

Send every group's `Agent` call in one message, `model: "sonnet"`. Each brief carries:

- the goal, Greg's answers from step 1, and the client test;
- a pointer to `~/Git/home-lab/docs/adding-a-service.md` and `CLAUDE.md`, not a retelling;
- **read-only**: it may read the repo, run read-only ssh commands on dungeon and unraid
  (`ls`, `docker ps`, `showmount`), and read the web; it edits and restarts nothing;
- sources: the project's own docs, its image repo and release notes first; then what
  self-hosters report (the `reddit` skill's `reddit-search.py` and `fetch-thread.py`),
  plus any links Greg gave. When Reddit answers 403 on moria, run the same commands
  through `ssh dungeon`;
- the output: a pitch at `<scratchpad>/pitch-<group>.md` with these sections:
  **Design** (and the alternatives rejected, one line each), **Touchpoints** (all twelve,
  each a concrete change or "n/a because …"), **Diff sketch** (the compose block, the
  Caddy handle, the probe target), **Greg's steps** (1Password items, phone apps, router
  changes, anything at a keyboard), **Risks** (memory, a fail-open path, data loss),
  **Commit message** (conventional, e.g. `feat(audiobookshelf): serve audiobooks from the
  audio-books share`), and **Sources**.

When groups depend on each other (a sync tool feeding an inbox), compare their pitches and
settle the shared contract before step 3: the first run's two pitches disagreed on where the
inbox lived. **Done when** every pitch has all twelve
touchpoints decided and you have checked each against the checklist yourself. A pitch with
a blank touchpoint goes back to its agent.

## 3. Pitch

Give Greg short bullets per group: the design in one line, his steps, the risks, the
commit message, and the pitch file's full path. Then one `AskUserQuestion` with a question
per group: **Approve**, **Approve with changes** (he writes them in Other), **Drop**. In
`deploy` mode skip the question and say you are proceeding.

## 4. Implement, one group at a time

An `Agent` with `isolation: "worktree"` makes the worktree in the repo of *your* current
directory, which is often toolbox. For home-lab work, `git worktree add` it yourself under
`~/Git/home-lab/.claude/worktrees/` and give the agent that absolute path.

The groups all edit the same files (compose, Caddyfile, `prometheus.yml`,
`backup-tier1.sh`), so build them **sequentially** in `~/Git/home-lab` on moria, never
in parallel. For each approved group, do it yourself or give one Sonnet agent the pitch
and the checklist. Then:

1. Apply every touchpoint in the pitch.
2. Run the repo tests the change touches, at least `monitoring-config.test.sh` and
   `backup-tier1.test.sh` under `scripts/tests/`. Fix until green.
3. Run `scripts/service-audit.py` (0 open gaps) and get a DeepSeek second opinion on any
   group with logic, via the `pi-ask` skill. Tell the worker to skip
   `backup-tier1.test.sh` (it outlasts pi's idle timeout) and cap `--max-turns`, or it
   reads forever and answers nothing.
4. Commit the group alone with its pitched message. No AI attribution lines: tell any
   agent that writes a commit the same.

Greg's steps that block a deploy (a new secret needs a 1Password item and `just secrets`
on dungeon over VNC) go to him in **one** batch, with the exact commands. Design around
new secrets where the app allows it.

## 5. Deploy and verify

**Push only the groups that can deploy now.** A pushed probe for a service that is not
running pages Greg, so a group waiting on him stays on a local branch. Then follow the Deploy section of the checklist: pull in `~/Git/home-lab` on dungeon
and `export COMPOSE_ENV_FILES` before any `compose up` over ssh. Then run every line of its
Verify section. **A group is done only when every verify line passes.** Paste the evidence.
A failure gets diagnosed and fixed before the next group deploys.

Ask before anything disruptive that the pitch did not name: recreating the gluetun group,
restarting a service other groups depend on, a router or DHCP change.

## 6. Report

Per group: the commit, the URL, the verify evidence, the steady-state memory, and what is
left for Greg (the client test, phone setup), each as an exact step. A new failure mode
gets its `docs/runbooks/` page in the same change. If this run taught something about
adding services in general, edit `docs/adding-a-service.md`; if it taught something about
running this skill, edit this file.
