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
