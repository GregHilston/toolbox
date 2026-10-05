---
name: compare-local-models
description: Compare a new local LLM against the models we run on moria and dungeon, using the repo's CRUD-app eval, and adopt it if it wins. Use when asked to test or compare a model, or to look for newer candidates.
argument-hint: "[model repo or name ...] | search"
disable-model-invocation: true
---

# Compare local models

Decide whether a new model should replace one we run. **The method, the incumbents'
numbers and the adoption checklist are in `~/Git/toolbox/docs/model-evaluation.md`.
Read it first and follow it**; this file only frames the job.

## The two jobs

Either way, read the doc's **Rejected** table first. Skip a model listed there unless
the doc's reason to re-test applies, and tell the user which ones you skipped.

- **Named models** (`/compare-local-models org/Model-X org/Model-Y`): test those.
- **`search`, or no arguments**: find candidates yourself. Check Hugging Face for
  releases newer than the incumbents (newest first, `mlx-community`, oMLX `oQ*` builds,
  `lmstudio-community`), and the r/LocalLLaMA and Hacker News skills for what people
  run on Apple Silicon. Shortlist at most three per role, say why each made it, and
  confirm the list with the user before downloading anything big.

## The machines

- **moria**: M4 Max, 128 GB, the dev laptop. Not always on. Runs a **light** model
  (pi's default, fast, every interactive turn) and a **heavy** one (dense, slow to first
  token, for hard coding).
- **dungeon**: M3 Pro, 36 GB, the always-on server. Runs only the **light** model,
  beside Docker and Frigate, and already sits near its memory limit.
- **citadel**: M5 Pro, 48 GB. Light model.

## What we prefer

- **MLX models served by oMLX**, strongly. A build oMLX cannot load is out.
- **Speed techniques are fine when quality holds**: lower-bit or mixed oQ quants, MTP.
  Measure each against the plain build; never assume it is free.
- **Quality comes first**, then speed, then memory. **Nothing may swap.**
- The light model needs **vision** and clean **tool calls**.

## Permissions

You may stop pi-web's session daemon and Hermes (on moria, and Hermes' containers on
dungeon) for the duration of a measurement, and restart oMLX on moria. **Start them
again when done** and check they are up; the commands are in the doc. Never stop
Frigate or other dungeon services, and never restart dungeon's oMLX.

## Finishing

Report a table of the candidates against the incumbents: correct by the end, correct
with no hints, time, decode, prefill, memory, swap. Give a recommendation per role.
Adopt only with the user's go-ahead, through the doc's checklist, then record the new
numbers in its incumbents table so nobody re-measures them.

A rejection is recorded too, also on the user's go-ahead: a row in the doc's
**Rejected** table (date, model, role tried for, why not), a dated section in
`docs/local-llm-benchmarks.md` with the numbers, and the weights and their settings
entry deleted.
