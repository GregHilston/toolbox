# Picking a model for delegated work: the detail

Read this before you route work to DeepSeek, `pi`, a local model or bulk generation. The global `CLAUDE.md` holds the short rules; this holds the routing detail.

## Claude subagents as builders

When Claude usage has room, builders are Claude subagents: Sonnet for size M or logic, Haiku for size S, with Sonnet plus Luna reviews (2026-11-13: eight tickets built and landed in one evening this way). Fall back to DeepSeek pi workers when the Claude window runs low.

## Headless Claude costs more quota

`claude -p` and Agent SDK sessions (`entrypoint: sdk-cli`/`sdk-ts`) use up the 5-hour window 1.8-2.9x faster than an interactive session for the same tokens, by several independent A/B tests in anthropics/claude-code#97074 (open on 2026-11-08). Prefer a pi worker or an interactive Remote Control session over a Claude `-p` worker.

## DeepSeek and the gateway

- **DeepSeek** (`pi-ask.py`) for every second-opinion review of a branch with logic in it, for bulk reading, and by default for implementation and research too, with Opus orchestrating (2026-11-01). Sonnet is for reading shots and tickets that parked twice. Use it from the start of a session, not as an afterthought.
- The gateway's `cloud` runs Zro's free plan, Command Code GOAT, OpenCode Go, GPT-5.6 Luna on ChatGPT Plus, then DeepSeek's API, with Luna before GOAT at DeepSeek's peak.
- `PI_CLOUD_MODEL=cloud-zro|cloud-goat|cloud-go|cloud-luna|cloud-deepseek` pins one (2026-11-16), but only `pi-ask.py` and gridkeep's `tools/land/` read it. A bare `pi` ignores it and falls back to `local-small` (`~/.pi/agent/settings.json`), so pass `--model`.
- "Use DeepSeek" means plain `--model cloud`, whose order is Greg's preference; pin a vendor only when he names one (2026-11-13).
- DeepSeek credit isn't scarce: a few dollars of real balance is more than a day of work. Don't reroute work to save it; just don't waste it.
- Run `deepseek-preflight.py` before starting DeepSeek work: it prints the rate now, minutes to the next peak, and the balance. Start long `pi` runs with `--off-peak`, so they wait out peak hours. A review costs cents, so run it even at peak price.

## Local models

- **No local model runs factory workers** (2026-11-18): Strata on moria decodes about 37 tok/s, one request at a time, so a median gridkeep or loser-picks ticket spends about 75 min in the model against about 21 on DeepSeek, and foundation is worse. Strata is for interactive pi, home-lab jobs and Hermes; the A3B stays the default for interactive use and scripts. When cloud credits run out, top up DeepSeek. This covers DeepSeek V4 Flash on ds4 and the Qwen A3B too (2026-11-19: slower still). Numbers: `~/Git/notes/llm/local-lane-strata-basalt.md`.
- **Bulk LLM generation** (playtest cohorts, batch labelling) runs on the free local model through oMLX. Luna's ChatGPT allowance is for small samples: run a 5-10 item pilot, read its gauge with `deepseek-preflight.py`, and keep a batch under 20% of the weekly allowance (2026-11-08).

## Briefing a delegated task

Point it at the repo's own rules for the task (a command, skill or `CLAUDE.md` section) rather than restating them. On 2026-10-21 a Haiku agent filed vault clips from Greg's hand-written spec, never saw `.claude/commands/triage.md`, and made a string of mistakes he had to catch. Clip writing is Sonnet work.
