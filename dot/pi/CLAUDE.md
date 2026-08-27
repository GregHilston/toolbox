# Pi (pi-mono)

Dotfiles for the pi coding agent, stowed to `~/.pi`.

## Secret Management

`models.json` contains the oMLX API key and is generated from `models.json.tpl` via `just secrets` (1Password `op inject`). `settings.json` is managed by home-manager (pi.nix) and contains no secrets.

Nothing else here holds a secret. The Reddit session cookie for
pi-reddit-research lives outside 1Password on purpose: `reddit-research.json` is
declared by pi.nix and points at `~/.config/pi-reddit-research/cookie.txt`, a
hand-edited file. Reddit expires the cookie every few days, and `cookieFile` is
re-read before every request — so refreshing it needs no rebuild, no
`just secrets`, and no restart.

## DeepSeek, and switching back to local

The default is unchanged and stays unchanged: a bare `pi` is `omlx` +
`defaultModel`, on this machine, free. DeepSeek is the opt-in alternative.

**It needs no `models.json` entry.** pi ships `deepseek` as a *built-in*
provider — `docs/providers.md` maps `DEEPSEEK_API_KEY` to it — so the moment the
env var exists, `pi --list-models deepseek` reports `deepseek-v4-pro` and
`deepseek-v4-flash` (1M context, 384K output, thinking, no images). Verified with
a dummy key on pi 0.84.2.

`api-docs.deepseek.com/quick_start/agent_integrations/pi_mono/` still tells you
to write a `providers.deepseek` block into `models.json`. **Do not.** A
hand-declared provider shadows the built-in catalog, and we would then own
`contextWindow`, `maxTokens` and `cost` by hand for a model whose numbers move.
The doc is written for a pi old enough to lack the catalog.

The three ways to reach it, cheapest first:

| | |
| --- | --- |
| In a session | Ctrl+P cycles `omlx` ↔ `deepseek`, or `/model` picks |
| From the shell | `pid` (v4-pro) / `pidf` (v4-flash), aliased in `dot/zsh/.zshrc` |
| One-off | `pi --provider deepseek --model deepseek-v4-flash` |

Ctrl+P only offers what `enabledModels` lists, which `pi.nix` builds as
`["omlx/*"] ++ optionals cfg.deepseek ["deepseek/*"]`.

### Where this fits against Claude Code

They are not competing for the same job. **Claude Code on Claude models stays the
interactive default** — the session you sit in front of and read step by step.
**pi on DeepSeek is for long unattended runs**, and the reason is the window: 1M
against oMLX's 262k. A wide refactor or a long combat-debugging run that would
force compaction locally simply does not here.

Cost is not the deciding axis at this scale (see below); latency and the window
are.

### Which model, and how much thinking

Both models reason, but they expose **different** thinking levels — the catalog
nulls the rest out, so Shift+Tab (`app.thinking.cycle`) cycles a shorter ring
than pi's seven levels suggest:

| | Shift+Tab cycles | in / out / cache-read per 1M |
| --- | --- | --- |
| **V4 Pro** | `off → high → max` | $0.435 / $0.87 / $0.003625 |
| **V4 Flash** | `off → low → high → max` | $0.14 / $0.28 / $0.0028 |

`--thinking <level>` sets the *starting* level for a session; Shift+Tab still
cycles from there. pi-powerline-footer reserves that key
(`APP_RESERVED_SHORTCUTS`) rather than consuming it, so the `think:` segment
tracks the real level.

For coding work in `~/Git/gridkeep`:

| Task | Model | Thinking |
| --- | --- | --- |
| Mechanical edits — renames, moving code, a `data.jsonc` field plus its GDScript mirror | Flash | `high` |
| Writing tests, docstrings, a script from an existing pattern | Flash | `high` |
| Reading code to explain it — tracing a call path | Flash | `high` |
| Anything unattended that will be merged | Pro | `high` |
| A failing golden test, or anything touching tick resolution / effect ordering | Pro | `high` |
| Balance judgment, "why did this board lose", designing a mechanic | Pro | `max` |
| Anything that should stay on the machine | omlx | — |

**Thinking is effectively free here; buy it.** The old advice was to spend
thinking only where a wrong answer costs a debugging cycle. That was written
against an estimate that turned out to be ~30x too high (see the measurements
below), so the levels above have been raised and `off` has been dropped
entirely. **Correctness of the merged diff is worth more than iteration speed.**
An unattended worker that thinks for an extra four minutes and lands a right
answer beats one that returns in two and needs a review round.

### What a run actually costs — measured 2026-08-27

Two gridkeep issues implemented unattended by `/orchestrate-pi`, Flash at
`high`, each in its own worktree, each running the full GUT suite per commit:

Three gridkeep issues, each: worker → Claude review subagent → the *same* worker
enacting review feedback via `--continue` → merged. Six pi passes total.

| | #64 one-line fix | #30 flag + 8 sites | #65 shared component |
| --- | --- | --- | --- |
| worker turns | 52 | 67 | 116 |
| worker cost | $0.0103 | $0.0151 | $0.0316 |
| worker wall | 3.6 min | 6.2 min | 8.7 min |
| review-pass turns | 45 | 22 | 39 |
| **review-pass cost** | **$0.0095** | **$0.0046** | **$0.0139** |
| cache hit, worker | 95.2% | 96.3% | 98.2% |
| cache hit, review pass | 99.4% | 99.4% | 99.5% |

**Three issues implemented, reviewed, revised and merged for $0.085.** All six
passes on Flash at `high`. Final suite 1855/1855, up from 1853.

**The review pass is the cheapest work in the run** — $0.0046 to enact three
fixes on #30. A `--continue` resumes a warm session, so billed input collapses
(3,993 tokens for #30's review pass against 44,113 for its worker) and nearly
everything is a cache read. Treat an adversarial review plus a feedback round as
effectively free; it is the highest-value token spend available here, and it
caught a vacuous test, a one-line-deletion anti-pattern and five stale comments
across the three issues.

**The cache is the whole story, and it inverts the old advice.** The ~16k floor
per request is real and it *is* re-sent every turn — but it is re-sent as a
**cache read**, at $0.0028/M on Flash against $0.14/M for fresh input, a 50x
discount. Hit rates were 95% and 98%, and they climb as a session lengthens,
so the longest runs are the cheapest per token. The floor is a latency story,
not a cost one.

Scaling that to Pro: Pro is 3.1x Flash on input, 3.1x on output, and 1.3x on
cache read. A #65-shaped run on Pro at `high` lands near **$0.06–0.09** — still
under a dime for an issue implemented, tested and self-reviewed. **There is no
budget argument for Flash.** Choose Pro when the diff will be merged, and Flash
when you want an answer fast and will read it yourself.

Thinking tokens bill as output and are the one thing that genuinely scales with
the level, but on the observed ratio (#65 spent 35.7k thinking tokens, $0.010 of
its $0.032) even `max` on Pro stays in cents.

**Speed, for planning a queue:** ~4.5 s/turn on Flash at `high`, near-flat
across both runs, and roughly 4.5 turns per minute of wall clock. A small issue
is ~50 turns, a medium one ~115. Budget **4–10 minutes of model time per issue**,
plus ~55s of GUT suite per commit, which is wall clock the model is idle for.

The prices, windows and level maps above are read out of pi's built-in catalog,
so they are exact. **Flash has still not been benchmarked against Pro on this
code.** What is now known is that the cost difference does not matter, so the
honest test is a quality comparison, not a cost one: the same issue at
Flash/`high` and Pro/`high`, diffed against each other.

### Extensions written here for orchestration

Three extensions in `dot/pi/.pi/agent/extensions/` exist for unattended
`/orchestrate-pi` runs. All three are **inert unless armed**, because a global
extension also loads in every interactive session and none of this belongs at a
keyboard.

| Extension | Armed by | What it does |
| --- | --- | --- |
| `orchestration-status.ts` | `PI_STATUS_FILE=<path>` | Rewrites a small JSON status file every turn and tool call: phase, turn, current tool *and its command*, the last thing the worker said, a short ring buffer of recent activity, `lastActivityAt`, `lastBlocked`, running tokens and cost. |
| `orchestration-guardrails.ts` | `<cwd>/.pi/guardrails.json` exists, or `PI_GUARDRAILS=1` | Blocks `git push`, `checkout main`, `merge`/`rebase`, `--no-verify`, `gh` writes, `pi install`, `/login`, and edits under `.pi/` — via `tool_call`, with a reason the model reads. |
| `extensions-available/sandbox/` | **parked, loaded by nobody** | Official pi example on `@anthropic-ai/sandbox-runtime`. Deliberately outside the auto-discovery root — see below. |

**Why status exists.** A pi worker that dies on spawn writes a 0-byte log; one
thinking hard writes nothing new. They are identical from outside, and two dead
workers were reported as "still running" before anyone ran `ps`. Now the worker
says so itself, and a *missing* status file means it never started — the case
that actually fooled us. Writes are atomic (temp + rename) so a poller reading
mid-write never sees half a document.

Liveness was the first question; *what is it doing* is the one asked every time
after, and `phase: "tool", currentTool: "bash"` does not answer it. So the file
also carries `lastToolBrief` (the command, not just the tool name), `lastText`
(the last thing the worker said out loud) and `recent`, a capped ring buffer of
the last eight actions. All of it is truncated and bounded on purpose: this file
is rewritten on every event and polled continuously, including by the status
line, so it must stay small no matter how long the run goes.

**Why guardrails exist.** "Never push, never merge, never `gh` write" were English
sentences in a 141-line prompt. That is a request, not a boundary, and nobody is
awake at 3am. `tool_call` can block, so they are boundaries now. The model
receives the reason verbatim, which is why the reasons say what to do instead.

The hard part was **not blocking the wrong thing**: a worker editing documentation
*about* pushing writes "git push" into a file, and a naive substring match blocks
that and gets itself diagnosed as broken. So commands are split into the segments a
shell would run, with heredoc bodies stripped first. Most of
`dot/pi/tests/orchestration-guardrails.test.ts` is about those false positives.

**Sandbox, measured 2026-08-27, and why it is parked.** It keeps the host
toolchain (`godot`, `uv`) because it sandboxes the bash tool rather than the pi
process — which is why building a Linux container image for this would have been
the wrong call. Filesystem confinement genuinely works: a write outside
`allowWrite` did not land.

It lives in `dot/pi/extensions-available/`, **outside** `.pi/agent/extensions/`,
and that placement is the whole point. Its `package.json` carries a `pi`
manifest, and pi auto-loads *any subdirectory with one* — no `-e` required. Its
`DEFAULT_CONFIG` is `enabled: true`. So simply having it in the extensions
directory turns OS-level bash sandboxing on for **every pi session on this
machine, in every project**. Worse, a global `sandbox.json` of
`{"enabled": false}` does **not** switch it off: sessions still hung with it in
place, and only removing the directory restored them.

Two measured failures keep it parked: a **denied write hangs the worker** rather
than erroring, and **network domain filtering hung a run outright**. To work on
it, load it explicitly:

```bash
pi -e ~/Git/toolbox/dot/pi/extensions-available/sandbox   # needs npm install first
```

`node_modules` is gitignored, so a fresh checkout needs `npm install` in that
directory before the `-e` will resolve. Tracked as gridkeep issue #82.

### Seeing what an unattended worker is doing

Three scripts in `bin/` turn a pi worker from a black box into something
readable. They are separate from the extensions because they run in the
*orchestrator's* process, not the worker's.

| Script | Reads | Answers |
| --- | --- | --- |
| `pi-narrate.py` | pi's `--mode json` stream, on stdin | "what is happening, right now, in words" |
| `pi-workers.py` | every `.pi/status.json` under a root | "which of my four workers needs me" |
| `pi-rpc.py` | pi's `--mode rpc` protocol | "change what this one is doing, without waiting for it" |

**The bug they were written for was ours, not pi's.** `/orchestrate-pi` spawned
workers as `pi ... > log.jsonl 2>&1`. Claude Code captures a background
command's output from a PTY, so redirecting everything to a file meant the
harness saw zero bytes and reported *"no output available"* for the entire run —
while pi had been emitting a fully detailed, line-buffered event stream the whole
time. We were discarding it at the shell and then reading a 13MB log back with
`jq` to recover a fraction of what we had thrown away.

`pi-narrate.py` goes in the pipe where the redirect was. It writes the raw JSONL
itself, so nothing is lost, and prints one line per event worth seeing. Two
non-obvious things it handles:

- **It splits records on LF only.** pi's `docs/rpc.md` is explicit that a generic
  line reader is not protocol-compliant, because it also splits on U+2028 and
  U+2029 — both legal inside a JSON string, and both of which appear in real
  model output. A text-mode `for line in stdin` corrupts records.
- **Non-JSON lines are surfaced, not dropped.** With `2>&1` those are pi's own
  stderr: the settings-lock warning, provider errors, stack traces. They used to
  vanish into the log unread.

`pi-rpc.py` is the one worth understanding before reaching for it. It runs the
worker under `--mode rpc` and holds a control socket open, so `pi-rpc.py steer`
reaches an agent that is *still working* — the message lands after the current
tool calls and before the next model call. Verified against a live worker: three
steps into a four-step task, a steer made it abandon the rest and comply on the
next turn. It deliberately keeps `-p`'s lifecycle (exit on `agent_settled`), so a
backgrounded run still ends and still notifies; `--keep-alive` opts out for
attended use. The socket lives in `$TMPDIR` under a hash of the worktree path,
not in the worktree, because macOS caps a Unix socket path at 104 bytes and a
worktree path plus `.pi/rpc.sock` gets close enough to matter.

None of this substitutes for reading the diff. A worker's narration is still the
worker's account of its own work, and a *convincing* narration makes the review
loop below easier to skip — which is the new failure mode, not the old one.

### Tests

```bash
just test                                              # both suites
cd ~/Git/toolbox/dot/pi && node --test 'tests/*.test.ts'   # extensions only
cd ~/Git/toolbox/tests && python3 -m unittest discover     # bin/ scripts only
```

Node 26 strips types natively, so there is no build step and no dependency; the
Python suite is stdlib `unittest` for the same reason. The `bin/` tests live in
`tests/` at the repo root rather than under `bin/`, because the recursive `$PATH`
glob in `.zshrc` would otherwise put a test directory on `$PATH`.

**Test files must not live in `.pi/agent/extensions/`.** pi scans that directory
and tries to load every `.ts` in it as an extension — a `*.test.ts` there is
loaded, *executed*, and then errors with "does not export a valid factory
function", which pollutes every pi session on the machine. They live in
`dot/pi/tests/` and import across.

### The review loop is practically free — use it every time

The single highest-value habit found in the 2026-08-27 run, and the one most
likely to be skipped for looking like overhead:

> worker commits → **fresh Claude subagent reviews the diff** → findings go back
> to the **same pi session** via `--continue` → worker enacts what it agrees with
> → verify → merge

A feedback pass costs **$0.005–$0.014** and hits **99.4% cache**, because
`--continue` resumes a session whose context is already warm — billed input drops
by an order of magnitude against the worker run that preceded it (3,993 tokens vs
44,113 on the same issue). Three issues cost $0.085 *including* all three review
passes.

Two details that make it work:

- **Back to the original worker, not a new one.** It still holds its own
  reasoning, so it can push back. Tell it to enact only what it agrees with and
  to justify what it rejects — across three issues the workers rejected two
  reviewer suggestions and were right both times.
- **The reviewer is Claude, not another pi.** One adversarial read is where
  judgement matters most, and it is a single cheap call.

Green suites do not substitute for it. In one short run it caught a test that
would have passed against a component that rendered nothing, a fix shaped like
the bug it was fixing, and seven stale comments describing removed behaviour —
with the suite green the whole time.

### Running pi unattended — what bites, and in what order

Found the hard way on 2026-08-27, driving `/orchestrate-pi` over gridkeep. Every
one of these fails **silently or misleadingly**; none announces itself.

**`--session-id` cannot be combined with `--continue`.** pi rejects the pair
outright: `Error: --session-id cannot be combined with --continue`. To push back
on a live worker, use bare `--continue` from the worktree's cwd (sessions are
keyed by project directory, so one worktree has exactly one session and it is
unambiguous), or address it explicitly with `--session <id>`. `--session-id` is
create-if-missing and is for *starting* an addressable session, not resuming one.

**A worker cannot create new files by default.** The global permission config
(`~/.pi/agent/extensions/pi-permission-system/config.json`) sets
`"write": {"*": "ask"}`, and `ask` with no UI resolves to
`confirmation_unavailable` — **blocked**, not queued and not prompted. The worker
can `edit` existing files but not `write` a new one, and it surfaces as the model
improvising around a denial mid-task. Fix per worktree with
`<worktree>/.pi/extensions/pi-permission-system/config.json` containing
`{ "yoloMode": true }`. Yolo is an ask→allow rewrite only — the `*.env`,
`~/.ssh/*` and reddit-cookie **denies survive it**, which is the whole reason to
prefer it over `--no-extensions`.

**That config needs `--approve` to load at all.** Non-interactive modes never
show a trust prompt, and `defaultProjectTrust` is unset (so: `ask`), which in
`-p`/`--mode json` means *silently ignore every project resource*. `trust.json`
currently trusts only `~/Git/notes`. **Pass `--approve` on every worker
invocation** or the per-worktree permission config is not read and nothing says so.

**`DEEPSEEK_API_KEY` is not in Claude Code's Bash environment**, even though
`.zshrc` exports it — the tool's shell does not pick it up. Source it explicitly
at spawn:

```bash
set -a; . ~/Git/toolbox/nixos/secrets/.env; set +a
```

Note the path is `$TOOLBOX_HOME/nixos/secrets/.env`, i.e.
**`~/Git/toolbox/nixos/secrets/.env`** — not `~/Git/nixos/secrets/.env`, which
does not exist and is the obvious wrong guess.

**`Invalid settings file … EPERM: mkdir settings.json.lock` is Claude Code's
sandbox, not pi.** `settings.json` is a read-only nix-store symlink and pi wants
a lockfile beside it. Under Claude Code's Bash sandbox that write is denied and
pi warns. Re-run with the sandbox off and it is silent. Do not go "fixing"
settings.json on the strength of it.

**Never combine a heredoc with a backgrounded `pi` in one shell command.** Writing
the prompt file and spawning the worker in the same `run_in_background` call
**silently produces nothing**: the heredoc writes fine, the harness reports the
command as running, no `pi` process ever starts, the redirect target is created at
**0 bytes**, and no completion notification arrives. It looks exactly like a worker
thinking for a long time. This cost two stalled workers in one run before anyone
looked at `ps`.

Write the prompt file in one call, spawn `pi` in the next as a bare invocation with
nothing else on the line. The diagnostic that settles it in seconds:

```bash
for p in $(pgrep -f "pi --provider deepseek"); do
  echo "pid $p  cwd: $(lsof -a -p $p -d cwd -Fn 2>/dev/null | grep '^n' | cut -c2-)"
done
```

An empty result plus a 0-byte log means it never started — that is a spawn bug, not
a slow turn. A live pid with a growing log means wait. `lsof` on `cwd` also catches
the other half of the trap: a worker started from an inherited working directory
rather than an explicit `cd`, which is how one ends up running in the wrong worktree.

**Reading usage out of `--mode json`.** Usage lands on `message_end` events, one
per assistant turn; sum those. `turn_end` and `agent_end` repeat the same
numbers, so counting them double-counts. Each event carries pi's own `cost`
object — prefer it to recomputing from a price table, which rots. `input` is
only the **uncached remainder**: read `totalTokens`, and read `cacheRead`
separately or you will conclude the run was expensive when it was not.
`gridkeep/.claude/pi-usage.py` does all of this.

**pi has no *built-in* sandbox, by design.** `docs/security.md` is explicit:
built-in tools read, write and run shell commands with the pi process's full
permissions. A git worktree is a merge-conflict boundary, not a security one.

An earlier version of this note said "no extension can add isolation". That is
wrong, and the official `sandbox` example disproves it: an extension can replace
the `bash` tool and route it through `sandbox-exec`, which confines the commands
without confining pi. What remains true is that extensions run with the pi
process's permissions, so an extension cannot contain *itself* — and prompt
injection through repo content is still expected local-agent risk. The documented options are in
`docs/containerization.md`: Gondolin (host pi, tools routed into a Linux
micro-VM — needs QEMU, **not installed here**), plain Docker/OrbStack (both
present), or OpenShell. For gridkeep specifically the blocker is the toolchain:
both Linux options mean the worker loses `godot` and `uv`, so it can no longer
run the suites that prove its own work. Real isolation there means **building an
image carrying godot 4.x + uv + python + dprint**, not flipping a flag.
`sandbox-exec` (macOS Seatbelt, what Claude Code itself uses) is the middle path
— filesystem confinement while keeping the host toolchain — but its network
control is all-or-nothing without a proxy.

### The key, and why citadel does not have one

`DEEPSEEK_API_KEY` follows `OMLX_API_KEY` exactly: a `op://` reference in
`nixos/secrets/.env.tpl`, injected by `just secrets` into `secrets/.env`, which
is gitignored and `set -a`-sourced by `.zshrc`. Nothing but the reference is
committed.

citadel is the Mozilla work machine and this is a personal metered key, so it is
withheld there — and withheld at the *key*, not at the menu. `just secrets`
`sed`s the line out of the template before injection on that host;
`custom.programs.pi.deepseek = false` additionally hides the models from the
picker so there is no dead menu entry. The justfile half is the load-bearing one.

Its guard is `hostname -s` = `citadel`. If that host ever answers to something
else, the key starts being injected there silently — the failure mode is quiet,
so check it if you rename the machine.

### Do not `/login deepseek`

Credential resolution is `--api-key` → `auth.json` → env var → `models.json`. A
`/login` writes to `~/.pi/agent/auth.json`, which would then outrank the env var
and give you two sources of truth — one of them with no host guard on it. That
file is a folded stow symlink into this repo; it is gitignored (root
`.gitignore`), so a key there would not be committed, but it would live on
citadel just fine.

Check the credential without spending a token:

```bash
pi auth check --provider deepseek --json
pi --list-models deepseek
```

### And especially do not `/login` to Claude

pi's `/login` menu offers **Claude Pro/Max** as a subscription provider, one
keystroke from where you pick anything else. Taking it points a third-party
harness at Claude on subscription credentials, which is a different arrangement
from the one this repo is set up for: Anthropic banned it 2026-04-04, reinstated
it 2026-05-13, and meters it against separate non-rollover *Agent SDK credits*
($20/mo on Pro, $100 on Max 5x, $200 on Max 20x), after which it bills at API
rates. Legitimate, but emphatically not "free with the subscription", and not
what `defaultProvider = "omlx"` and the DeepSeek wiring here are for.

The division this repo assumes: **Claude Code on Claude models** for interactive
sessions, **pi on DeepSeek or oMLX** for everything pi does. Claude Code shelling
out to pi is ordinary tool use and carries none of the above; pi holding an
Anthropic credential is the thing to avoid. `/orchestrate-pi` is built on exactly
that split.

`auth.json` is `{}` today. Keeping it that way is the whole control.

## Reddit cookie refresh

`pi-reddit-research` needs a Reddit session cookie; Reddit has required auth on
its `.json` endpoints since mid-2026 and expires the cookie every few days.

**It cannot be truly automated.** Reddit's login is interactive — password,
CAPTCHA, 2FA — and exposes no refresh-token flow, so nothing can *obtain* a
session unattended.

What is automated is *copying* one you already have. `bin/reddit-cookie-sync.sh`
runs daily on moria (`launchd.user.agents.reddit-cookie-sync`) and lifts
`reddit_session` out of Firefox's cookie jar, which is unencrypted SQLite on
macOS — unlike Chrome and Safari, which seal theirs with a Keychain key. As long
as you stay logged into reddit.com in Firefox, pi's copy stays current with no
typing.

The script is deliberately conservative:

- It probes the **existing** cookie first and no-ops if it still works, so it
  can never replace a good cookie with a staler one from Firefox.
- It probes the **new** cookie before writing, so a dead Firefox session cannot
  overwrite a working file.
- It checks the returned post count, not just the HTTP status — Reddit answers
  200 with an empty `children` array when unauthenticated.
- It writes through a mode-600 temp file and `mv`, so the cookie is never
  briefly world-readable.

### First-time setup, and the only recurring manual step

Both are the same action, so there is nothing separate to remember:

1. Open **Firefox** (not Chrome or Safari — macOS encrypts their cookie jars
   with a Keychain key, so they cannot be read without prompting).
2. Go to <https://reddit.com> and log in. Stay logged in; do not use a private
   window, and do not tick anything that clears cookies on exit.
3. Run `~/Git/toolbox/bin/reddit-cookie-sync.sh` once to seed the cookie, or
   just wait for the daily agent.

That is the whole procedure. There is no cookie to copy, no devtools, no
`token_v2` — `reddit_session` alone authenticates, which the sync script and
`fetch-thread.py` both rely on.

When the session lapses, the script posts a macOS notification and you repeat
step 2. Nothing else changes: no rebuild, no `just secrets`, no restart.

Confirm it worked:

```bash
~/Git/toolbox/bin/reddit-cookie-sync.sh    # "OK: ..." on either path
fetch-thread.py https://www.reddit.com/r/NixOS/comments/<id>/
```

If the script reports it cannot find a `reddit_session`, Firefox is logged out
or you are looking at a different Firefox profile — it scans every profile under
`~/Library/Application Support/Firefox/Profiles/` and takes the first with a
cookie, so a second profile that is logged out is not a problem, but *no*
profile being logged in is.

The next daily run picks it up. To force it immediately:

```bash
~/Git/toolbox/bin/reddit-cookie-sync.sh          # or check the log:
tail ~/Library/Logs/reddit-cookie-sync.log
```

No restart is ever needed — `cookieFile` is re-read before every request, so
neither pi nor PI WEB's session daemon has to be bounced.

Only moria runs the agent. Other hosts keep working off whatever
`~/.config/pi-reddit-research/cookie.txt` holds and can run the script by hand.
(Upgrade path if the notification is too quiet: home-lab has Pushover
credentials, but they live in *its* secrets on dungeon, not in toolbox's.)

## Working across toolbox and home-lab in one session

The two repos are coupled — toolbox owns dungeon's machine config, home-lab owns
the containers on it — so a single question often spans both. But a pi session
has one working directory, and moonpi's `cwdOnly` guard blocks the file tools
outside it (`guards.ts`: it checks `read`, `write`, `edit`, `grep`, `find`,
`ls`; note `bash` is *not* path-guarded).

`moonpi.json` therefore names both repos in `guards.allowedPaths`. Start the
session in whichever repo the task is mostly about — you keep that repo's git
context, PI WEB's worktree-derived workspaces, and its `CLAUDE.md` — and the
agent can still read and edit across into the other.

Deliberately the two repos and not `~/Git`: that would open all ~40 repos and
leave the guard doing nothing. Verified after changing it that `~/Git/ccs` and
`~/.ssh/config` are still blocked.

The tradeoff is real — an agent working in toolbox can now edit home-lab without
being asked. That is wanted here because the repos are two halves of one system,
but it is not a reason to keep adding paths.

Nothing is needed on the PI WEB side: `pathAccess.allowedPaths` is already
`~/Git`, so its file explorer can browse both. That setting only governs PI WEB's
own UI/API, never what the agent can touch — the guard above is the real control.

## The token budget (read this before adding an extension)

pi runs here against **local** models via oMLX by default. Every tool schema and
every line
of injected system prompt is re-sent on **every request**, so an extension is not
free just because it is popular. Measured on this host with
`pi --mode json -p ... | jq .usage`:

| Configuration | tokens/request |
| --- | --- |
| bare pi, no packages, empty dir | 1,644 |
| our stack, empty dir | 7,957 |
| our stack, `~/Git/toolbox` | 11,652 |
| our stack, `~/Git/home-lab` | 36,120 |

These were taken before moonpi was dropped (b7b8bf6/9641740) and are now high:
the same `~/Git/toolbox` measurement reads ~10,400 today. Re-measure the whole
table rather than trusting a single row against it.

Two things that are easy to misread:

**`usage.input` is not the prompt size.** oMLX prefix-caches, so `input` is only
the *uncached* remainder; the real figure is `totalTokens` (or
`input + cacheRead`). A reading of "1,356 tokens" that is really 34,139 will send
you in exactly the wrong direction.

**Caching hides latency, not capacity.** In `home-lab`, 36k of a 262k window is
gone before you type. Cache hits never give that back. Most of that 36k is
`home-lab/CLAUDE.md` itself — 103,738 bytes, ~25,934 tokens — loaded natively by
pi. That is a real cost of a 1,600-line context file, and it is a deliberate
choice rather than a bug.

**On DeepSeek every token in that table is billed, every turn.** The numbers
above are a latency-and-capacity argument while we are on oMLX; point pi at
`deepseek` and the same numbers become a per-request bill, paid before you type.
`home-lab`'s 36k floor is the one that stings, and most of it is that repo's own
`CLAUDE.md`. Nothing in "Rejected, with reasons" gets *easier* to justify on a
remote provider — read that section as stricter there, not looser.

To measure after any change:

```bash
pi --mode json -p 'Reply with exactly: OK' 2>/dev/null \
  | python3 -c "import sys,json;[print(json.loads(l).get('message',{}).get('usage')) for l in sys.stdin if '\"usage\"' in l][-1:]"
```

### Why moonpi was removed

It cost ~21k tokens/request in toolbox and ~59k in home-lab, entirely from
`contextFiles` — on by default, walking four directory levels and injecting every
`README.md` it found into the system prompt. It bought none of the three things
it was installed for: its guard never checked `bash`, its read-before-write was
redundant with pi's `edit` (which needs a unique exact `oldText`), and its plan
mode advertised tools it then blocked, costing a wasted round trip each time.
Replaced by `@gotgenes/pi-permission-system` and `@narumitw/pi-plan-mode`.

### Rejected, with reasons

- **pi-lens** (42k/mo) — ~3,600–4,600 tok/request floor from 7 always-active
  tools plus 4 skills, none individually disableable, and it spawns language
  servers. Its own maintainer documents (issue #1453) that its lazy-tool
  mechanism forces a full conversation-prefix rewrite on every non-Anthropic
  provider, i.e. a full re-prefill here. `tsc --watch` in another terminal is
  free.
- **pi-cache-optimizer** (11k/mo) — its prompt-slimming targets
  `<session-overview>` blocks and skill compression; we emit neither and have no
  pi skills. Its `prompt_cache_key` reaches oMLX, which returns 200 and ignores
  it. It would also hoist `CLAUDE.md` out of pi's `<project_instructions>`
  wrapper, and its integrity guard cannot detect that (the regex only matches
  attribute-less tags).
- **pi-mcp-adapter** (548k/mo, the #1 pi package) — genuinely the right design
  (~750–900 tok flat regardless of server count, versus 5,000+ for a natively
  registered server). **Deferred, not rejected**: the only MCP servers configured
  here are `sentry` and `godot`, neither worth bridging into pi. Install it the
  day there is a server worth the ~800 tokens, with `scriptMode: false`,
  `directTools: false`, and per-server `includeTools`.

## Reddit tools: kept global, and how to scope them

`pi-reddit-research` costs ~2,151 tok/request for 7 tools. It stays global
because that is an eighth of what moonpi cost, and because the tool-selection
worry did not materialise — asked "what does bin/reddit-cookie-sync.sh do when
Firefox is logged out?", a prompt containing the word *reddit* about a local
file, the model went straight to `read` rather than `reddit_search`.

If it ever does become a problem, scope it to one repo:

```jsonc
// <repo>/.pi/settings.json   — commit this; per-repo, not global
{ "packages": ["npm:pi-reddit-research"] }
```

and remove `"npm:pi-reddit-research"` from `packages` in
`nixos/modules/programs/tui/pi.nix`. Three things must then line up, and two of
them fail silently:

1. **Trust the project.** pi only loads `.pi/settings.json` once the directory is
   trusted. Non-interactive modes (`-p`, `--mode json`, `--mode rpc`) **never
   prompt** — they fall back to `defaultProjectTrust: "ask"` and ignore the file
   entirely. Use `/trust` once, or `--approve` for a single run.
2. **Install it there.** A trusted project auto-installs missing project packages
   at startup; `pi install -l npm:pi-reddit-research` is the explicit form.
3. **Check the cookie.** Expired Reddit auth looks like empty results, not an
   error. See the Reddit cookie refresh section above.

Verify with a real tool call, not the slash command — in `-p` the model tends to
go looking for `/reddit` in the repo instead of running it:

```bash
pi -p 'Use the reddit_search tool to search Reddit for "nixos flakes". Report the count.'
```

## Web search

`extensions/web-search.ts` registers a `web_search` tool against our self-hosted
SearXNG on dungeon. There is no API key, which is the point — it replaced a paid
Brave Search key.

The endpoint is not a literal in the extension. Only nix knows each host's answer
(localhost on dungeon, the tailnet address everywhere else), so
`custom.programs.pi.searxngBaseUrl` writes `~/.pi/agent/searxng.json` and the
extension reads it. `PI_SEARXNG_URL` overrides for a one-off.

### Gotcha: SearXNG returning zero results for everything

SearXNG answers HTTP 200 with an empty `results` array when its engines are
blocked, so a broken instance looks identical to a query with no matches. The
`unresponsive_engines` field is the tell, and `web_search` surfaces it rather
than reporting "no results". See `home-lab/searxng/settings.yml` — engines that
block a self-hosted instance rotate over time.

## Status line — pi-powerline-footer

Replaces pi's footer with model, thinking level, context percentage and token
counts. Declared in `nixos/modules/programs/tui/pi.nix`, both the package and its
`powerline` config block — and again in `hosts/macs/citadel/default.nix`, which
`mkForce`s the whole packages list, so anything added to the module default has
to be added there too or citadel silently misses it.

It is more than a footer: it also swaps pi's editor component, adds a sticky
bash mode (`ctrl+shift+b`), an editor stash (`alt+s`), a prompt queue, and
overrides `/compact`. The layout keeps `shell_mode` and `queue` for that reason —
they self-hide when empty, and are the only indication you are in one of those
modes.

Chosen over `@narumitw/pi-statusline` on installs (23.3k/mo against 12.5k) and
because its settings live in the `settings.json` pi.nix already generates rather
than a second file.

**It is free.** A/B'd on this host from the same cwd with only the package and
its config differing: 10,395 / 10,406 tok/request without it, 10,388 / 10,389
with. The delta is inside run-to-run thinking-token noise. It registers no tools
and injects no system prompt, so there is nothing to re-send.

**`workingVibe = "off"` is defensive, not required.** Vibes are already inert
when the key is absent — `working-vibes.ts` derives a `theme` from it and every
entry point returns early on a null theme, so `workingVibeMode` defaulting to
`"generate"` against `openai-codex/gpt-5.4-mini` never fires by itself. Pinning
`"off"` is what stops a stray `/vibe pirate` in one session from leaving later
sessions calling a model oMLX does not serve. `"file"` mode is the zero-cost way
to actually have the phrases.

**Its slash commands cannot persist anything.** `/powerline <preset>`, `/vibe`
and friends write back to `~/.pi/agent/settings.json`, which is a read-only
`/nix/store` symlink. They apply for the current session, then warn
`not persisted; check settings.json` and log an `EACCES` — pi does not crash, and
the write cannot damage the symlink. Change the nix and re-activate instead.

**Glyphs are picked per terminal, not per installed font.** `icons.ts`
`hasNerdFonts()` checks `POWERLINE_NERD_FONTS`, then `GHOSTTY_RESOURCES_DIR`,
then a `TERM_PROGRAM` allowlist (iterm, wezterm, kitty, ghostty, alacritty). So
Ghostty gets glyphs and keeps them inside tmux, where `TERM_PROGRAM` is `tmux`
but Ghostty's own variable survives. rohan's kmscon TTY and any ssh into dungeon
get the ASCII fallback no matter which fonts are installed there, because neither
variable is forwarded. Nothing forces it either way; `POWERLINE_NERD_FONTS=0`/`1`
is the override. The `ascii` *preset* does not do this — it only changes
separators, leaving the segment icons as Nerd Font glyphs.

**`context_pct` disappears if another extension claims compaction.** Both context
segments start with `if (ctx.customCompactionEnabled) return { visible: false }`,
and that flag is set when an extension publishes a `compact-policy` status key.
We run `pi-agent-suite`'s `custom-compaction`, which today publishes no such key —
so the segment renders. If a future version does, the whole point of this
extension silently vanishes and this is the first place to look.

## Gotcha: Context Window Errors

Pi's `models.json` declares per-model context windows, but oMLX enforces a **global** `sampling.max_context_window` in its own settings (`dot/omlx/.omlx/settings.json`). If pi reports "exceeds max context window" with a suspiciously low limit, check the oMLX server config — not just pi's model definitions.
