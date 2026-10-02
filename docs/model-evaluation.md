# Evaluating a local model against the incumbents

How we decide whether a new model (Qwen 4, a new Swift, a non-Qwen family) replaces one
we run. Written after the 2026-10-02 evaluation; the `/compare-local-models` skill
follows this page. `docs/local-llm-benchmarks.md` holds the history and every finding;
this page holds the method and the numbers a new candidate must beat.

## Hosts and roles

| host | machine | role | models |
|---|---|---|---|
| **moria** | M4 Max, 128 GB | dev laptop, not always on | **light** (pi default) + **heavy** (hard-coding specialist) |
| **dungeon** | M3 Pro, 36 GB | always-on server: Docker, Frigate, Hermes, Old Gregg | **light** only, as profile `:lab` (thinking off) |
| **citadel** | M5 Pro, 48 GB | second Mac | **light** |

Nix owns which model is where: `services.omlxDeploy.lightModel` (every oMLX host) and
`services.omlxDeploy.models` (extras, per host) in `nixos/modules/darwin/omlx.nix`.
`just dr <host>` writes `~/.omlx/models.manifest` and `bin/omlx-models.sh` fetches what
is missing. Swapping a model is a one-line change there plus the four places in
"Adopting a winner".

## What we want

- **MLX, served by oMLX.** No second inference server. A checkpoint must load in the
  oMLX we run: check its `config.json` `model_type` against
  `$(brew --prefix omlx)/libexec/lib/python3.11/site-packages/mlx_{lm,vlm}/models/`.
  Builds that need a patched runtime (ukisai's own Swift MLX repos) are out.
- **Speed tricks are welcome when quality holds**: smaller quants, oQ mixed-precision
  quants, MTP. Each must be measured against the unaccelerated build, not assumed free.
- **Quality first.** A faster model that finishes correct less often loses.
- **No swap growth**, on any host, for any model we keep: `swap_growth_mb` must be 0.
  (Absolute swap is not the test; dungeon carries some from its containers.) On dungeon
  this is checked with Docker and Frigate up, because they hold ~12 GB.
- **The light model needs vision** (Frigate reviews and Old Gregg send images on
  dungeon) and **must emit well-formed tool calls** (pi and Hermes).
- **The heavy model is moria-only** and can be slow to first token; it must be right.

## The incumbents (do not re-measure; beat these)

Measured 2026-10-02, oMLX 0.7.0rc1. Raw runs: `dot/omlx/bench/crud/results/<arm>/`.
`python3 dot/omlx/bench/crud/summarize.py` prints every arm. Re-measure an incumbent
only after an oMLX upgrade, a harness change, or if a candidate's numbers look off.

| role | model | CRUD correct by the end | correct, no hints | gen time | decode | prefill (16K / 64K) | resident | swap growth |
|---|---|---|---|---|---|---|---|---|
| light, moria | `Qwen3.6-35B-A3B-4bit` (temp 0.6, thinking on) | 1 of 3 | 0 of 3 | 3.4 min | 112 tok/s | 1,162 / 756 tok/s | 21 GB | 0 |
| light, dungeon | `Qwen3.6-35B-A3B-4bit:lab` (thinking off) | 0 of 2 (both 15/16) | 0 of 2 | 3.6 min | 53 tok/s | not measured | 21 GB | **+0.9 GB** in a 5.6k-token turn |
| heavy, moria | `Swift-1.5-Qwen3.8-27b-oQ4e-mtp`, `mtp_enabled` (temp 1.0, effort medium) | 3 of 3 | 2 of 3 | 3.4 min | 38 tok/s | 183 / 129 tok/s | 16 GB | 0 |

dungeon fails the no-swap-growth rule today: with its 56 containers up it started at 1.0 GB of
swap and reached 1.9 GB during one turn. Freeing RAM there is open work; a smaller light
model is the other lever.

The thinking budgets differ: 8192 tokens for the A3B, 16384 for Swift. Equalise them
(the `thinking_budget_tokens` entry) when a comparison hinges on it.

Also measured, and what they lost on, in `docs/local-llm-benchmarks.md` → "2026-10-02":
base Qwen3.8-27B oQ4e, Swift oQ5e/oQ6e, the A3B 6-bit, Qwen3.8-Flash-Next REAP-288.

## Procedure

Run on moria, in a session that can stop the box's other oMLX clients. Expect two to
four hours per candidate, most of it the dense runs.

### 1. Pick candidates

Asked for specific models: use those. Otherwise search, newest first:

```bash
curl -s "https://huggingface.co/api/models?search=<family>&sort=lastModified&limit=50" | python3 -m json.tool
```

Look at `mlx-community`, oMLX-quantized (`oQ4e`, `oQ5e`, `-mtp`) and `lmstudio-community`
builds; fetch sizes with `?blobs=true`. Read the base model's card for its official
sampling and any reasoning knob. Rule a candidate out before downloading if:
its 4-bit does not fit the role's budget, or oMLX lacks its architecture. Light: no
bigger than today's 21 GB, since dungeon already swaps a little at that size
(home-lab `docs/local-llms.md`). Heavy: about 70 GB, beside the light model on moria.

### 2. Install it for the test

```bash
$(brew --prefix omlx)/libexec/bin/hf download <repo> --local-dir ~/Git/toolbox/dot/omlx/.omlx/models/<dir>
```

Add a `model_settings.json` entry before the first request: the card's sampling, and
for a Qwen3.8-family template `chat_template_kwargs.reasoning_effort: medium` — its
default `xhigh` never terminates. oMLX reads the file on restart, which the harness does.

### 3. Quiet the box

Anything else calling oMLX skews speed and can trigger restarts mid-request.

```bash
launchctl bootout gui/$(id -u)/ai.hermes.gateway
launchctl bootout gui/$(id -u)/com.pi-web.sessiond
pgrep -fl hermes_cli          # kill what survives the bootout
```

Put them back when done, and check:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.pi-web.sessiond.plist
launchctl list | grep -iE "hermes|pi-web"
```

On dungeon, Hermes is the `hermes` and `hermes-ops` containers in home-lab;
`docker stop`/`docker start` them. Never stop Frigate or the rest: dungeon's numbers
must be taken with them up.

### 4. Quality: the CRUD eval, three runs per arm

The grader drives Chromium through `playwright-core`, kept in `~/.cache/crud-eval-grader`.
`crud_eval.py` installs it on first use and stops before round 0 if Chromium will not
launch, so a broken grader cannot silently zero the five UI checks.

```bash
~/Git/toolbox/dot/omlx/bench/crud/chain.sh <model>=<arm> <model>=<arm>-r2 <model>=<arm>-r3
EXTRA_ARGS="--host dungeon" ~/Git/toolbox/dot/omlx/bench/crud/chain.sh <model>=dungeon-<arm>
python3 ~/Git/toolbox/dot/omlx/bench/crud/summarize.py
```

What it is: `PROMPT.md` asks for a one-table SQLite + React CRUD app as files; the model
runs nothing. `crud_eval.py` installs and runs the app and scores 16 checks, five of them
in a headless browser. Failures go back verbatim as the next turn, at most two; each is
saved as `hints-round-N.md`, and **no hand-written hints**. Score a model by how often it
finishes 16/16 and how often with no hints. Nearly every model's first try pins a
`better-sqlite3` too old for Node 26, so first-try scores are mostly 1/16; recovering
from that error is part of the test.

`chain.sh` restarts oMLX before each arm, so only that model is resident. `--host` runs
generation on another host and grades here; it never restarts a remote server. Never
start a second run while one is going: a restart kills the other's request.

### 5. Speed and memory

- **Decode**: from the CRUD runs (`decode_tps`).
- **MTP**, if the checkpoint has an MTP head: make a twin, a symlink `<dir>-nomtp` to the
  model dir, and give each its own `model_settings.json` entry, one with
  `"mtp_enabled": true` and one without. Then
  `python3 ~/Git/toolbox/dot/omlx/bench/mtp_paired.py <off-id> <on-id>`. It samples on
  and off alternately, so thermal drift cancels, and reports whether greedy output
  matches. Then run the CRUD eval with MTP on: speed alone does not adopt it. Remove the
  twin and its entry afterwards. (The 2026-10-02 MTP arms are recorded under the old
  twin id `…-lmtp`, which was MTP-on; it no longer exists.)
- **Prefill**: `python3 ~/Git/toolbox/dot/omlx/bench/longctx.py <model>`. It matters
  most for agent turns over a large context.
- **Swap**: every CRUD run records `swap_growth_mb` (peak minus start); `summarize.py`
  prints the worst round. Must be 0.

### 6. Decide

1. More often 16/16 by the end than the incumbent, or equal with fewer hints.
2. Then, for the light model, decode and prefill — it runs every interactive turn.
3. Then memory: smaller wins ties, and anything that swaps is out.

An n of three is small. A one-run difference is noise; treat only a clear gap (the
dense 27B's 10 of 10 against the A3B's 2 of 5) as a result.

### 7. Adopting a winner

1. `nixos/modules/darwin/omlx.nix` `lightModel.dir`/`.repo` (pi and opencode default to
   it on every Mac), or `models` in `hosts/macs/moria`.
2. `dot/omlx/.omlx/model_settings.json`: the entry's settings and why.
3. `dot/pi/.pi/agent/models.json.tpl`, and `is_default` in `model_settings.json` for a
   new light model.
4. `bin/hermes-mode.sh` (`worker_local` light, which also does compression; `judge_local`
   heavy). On dungeon, home-lab's `hermes/config.yaml` names `<light>:lab`, a profile in
   this repo's `dot/omlx/.omlx/model_profiles.json`.
5. This page's incumbents table, and a dated section in `docs/local-llm-benchmarks.md`.
6. Verify pi and Hermes use it (below), then `just dr <host>` everywhere.

Delete rejected weights (they are re-downloadable); a model on disk with no settings
entry gets the template's defaults if anything ever asks for it.

## Checking pi and Hermes really use a model

Check oMLX's log, not the client's config: `grep "Chat completion"
~/.omlx/logs/server.log | tail`.

- **pi 0.87.1 ignores `--model` on the command line**; `pi -p --model X` talks to the
  default. Switch inside a session (`/model`, Ctrl+P), or over `pi --mode rpc` with a
  `set_model` command. pi's permission system refuses reads outside the working
  directory in `-p` mode, so test tool calls on a file in it.
- **Hermes**: run it with an argument list, not a shell string. This shell's command
  rewriter mangled `hermes chat -Q -q "…"` into argument errors every time:

  ```bash
  python3 -c 'import subprocess; print(subprocess.run(["hermes","chat","-Q","-m","<model>","--provider","custom","-q","Use your terminal tool to run: wc -l /etc/shells . Reply with only the number."],capture_output=True,text=True,stdin=subprocess.DEVNULL).stdout[-300:])'
  ```

  On dungeon, prefix the list with `"docker","exec","hermes"`.

## Traps we hit

- `ps -o comm` truncates to 16 characters, so `$1 ~ /python/` never matched and a
  queued run started on top of a live one. Wait on files the run writes, or `pgrep -f`
  a string that is not in your own wait loop.
- oMLX keeps every served model resident; the harness restarts it per arm for that
  reason (`dot/omlx/bench/README.md`, rule 1).
- Sequential speed comparisons on this laptop drift 15–30% as it heats. Pair them.
- The auto-mode safety policy blocks an unattended pi worker with `yoloMode`, which is
  why the eval has the model write files rather than drive pi's tools.
