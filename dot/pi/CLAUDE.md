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

## Web search

`extensions/web-search.ts` registers a `web_search` tool against our self-hosted
SearXNG on dungeon. There is no API key, which is the point — it replaced a paid
Brave Search key.

The endpoint is not a literal in the extension. Only nix knows each host's answer
(localhost on dungeon, the tailnet address everywhere else), so
`custom.programs.pi.searxngBaseUrl` writes `~/.pi/agent/searxng.json` and the
extension reads it. `PI_SEARXNG_URL` overrides for a one-off.

### Gotcha: moonpi silently strips third-party tools

moonpi calls `setActiveTools()` with a closed allowlist per mode. Before
**v0.4**, that allowlist was hardcoded to moonpi's own tools, so *every*
third-party tool — `web_search`, all the `reddit_*` tools, pi-fff — vanished
with no error. The model simply reported it had no such tool, which reads like a
bug in the extension rather than in moonpi.

The fix is `"preserveExternalTools": true` in `moonpi.json`, which unions
external tools into the allowlist. It needs moonpi ≥ v0.4 — the option parses on
older versions but is never read, so it looks set and does nothing. If a tool
disappears again, check moonpi's version first:

```bash
git -C ~/.pi/agent/git/github.com/galatolofederico/moonpi describe --tags
pi update --extensions
```

### Gotcha: SearXNG returning zero results for everything

SearXNG answers HTTP 200 with an empty `results` array when its engines are
blocked, so a broken instance looks identical to a query with no matches. The
`unresponsive_engines` field is the tell, and `web_search` surfaces it rather
than reporting "no results". See `home-lab/searxng/settings.yml` — engines that
block a self-hosted instance rotate over time.

## Gotcha: Context Window Errors

Pi's `models.json` declares per-model context windows, but oMLX enforces a **global** `sampling.max_context_window` in its own settings (`dot/omlx/.omlx/settings.json`). If pi reports "exceeds max context window" with a suspiciously low limit, check the oMLX server config — not just pi's model definitions.
