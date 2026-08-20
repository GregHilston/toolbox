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

When it cannot help — logged out of Firefox, cookies cleared, session lapsed
there too — it posts a macOS notification telling you to log in again. That is
the manual step, and it is the only one:

```
Open reddit.com in Firefox and log in. That is it.
```

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
