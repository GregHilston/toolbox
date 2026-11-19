# Asking Greg to choose: visual options, designs, tools and spends

Read this before you put a design, visual or tooling pick to Greg. The global `CLAUDE.md` points here.

## Visual options (concepts, models, layouts)

- Send one labelled grid, a row per item, then one `AskUserQuestion` with a question per item and a short line per option. Keep what he didn't pick (2026-11-13).
- Post before and after screenshots on the ticket for every visible change, so he can judge it without opening anything (2026-10-26).

## Any decision question

- Explain any game mechanic or term in one plain line first; he forgets names (rider damage, the action cap, 2026-10-26).
- Write what you decide onto the tickets, not only into notes.

## Picks that rest on a fact

- **API:** call it before offering the pick. On 2026-10-30 he chose a collector for "true hourly numbers" that AdGuard's API doesn't have on a 30-day window; the build found it only after he'd answered.
- **Game rule:** read the code before describing it (2026-10-31, a lock). Cite a source for another game's rule, not memory (2026-11-12, he asked "Is that true?" about ROUNDS).
- **Link:** load it and check it shows what he is meant to see (2026-11-12, two Fava links showed empty journals).
- **Echoed value:** when a response echoes a value other than the one you sent, find out why before building on it. On 2026-11-12 an image call answered quality `low` to a `high` request, and a tool and a retry loop were built before research showed quality can't be set on that route.
- **His free-text answers** often change the design: read them before filing, and put them on the ticket as soon as the round ends.

## A tool or a spend

Before the pick, say what the tool is, what it buys beyond what he already runs, and the whole workflow it serves. On 2026-11-16 he asked twice what `hc` was before he could answer a setup pick about it. On 2026-11-12 he paused an image-API pick to ask what happens once a concept exists, and the answer changed what the images were for (card icons only, map mood pieces only).

## "Think about it and propose" and "I'm new to this"

- "Think about it and propose": bring one proposal built on the project's own numbers and outside evidence (other games, community threads), with its reasoning, not a fresh set of bare options (2026-11-08).
- "I'm new to this, google best practices and repose": research first, save what you learn in the project's docs, then ask again with the evidence in the question (2026-11-12, LLC ledger layout).

## "Cut a ticket to explore"

File it and start the read-only spike at once, then bring its numbers back as a pick. On 2026-11-10 that turned a matchmaking question into a built feature within two hours.
