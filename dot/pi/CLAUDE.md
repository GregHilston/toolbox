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

pi runs here against **local** models via oMLX. Every tool schema and every line
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
