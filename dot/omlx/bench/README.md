# oMLX benchmark harness

The scripts behind `docs/local-llm-benchmarks.md`. Each is standalone and talks to a running
oMLX server on `127.0.0.1:8000`.

## Setup

The key is read from `$OMLX_API_KEY`, or from an `omlx_key` file beside these scripts.
**That file is gitignored — never commit it.** Every other secret in this repo goes through
1Password / `op inject`; this is the one runtime credential that does not.

```bash
export OMLX_API_KEY=$(python3 -c "import json,os;print(json.load(
  open(os.path.expanduser('~/.omlx/settings.json')))['auth']['api_key'])")
```

## Scripts

| script | measures |
|---|---|
| `bench.py` | decode throughput + TTFT, 3 reps over code/prose/qa |
| `codeeval.py` + `tasks.py` | 10 original coding tasks with executable assertion suites |
| `effort.py` | token/latency cost of each `reasoning_effort` level |
| `longctx.py` | prefill cost vs prompt length (~2K–64K) |
| `lossless_check.py` | whether an optimization changes output at all |
| `moe_quant_paired.py` | **the one to copy for A-vs-B**: alternating samples, so drift cancels |
| `moe_quant_showdown.sh` | A3B-4bit vs its 4-bit-DWQ sibling, decode + prefill, one arm at a time |  *(superseded — see below)*
| `moe_quant_verdict.py` | those raw numbers -> seconds per agent turn at a measured workload mix |
| `contention_audit.sh` | certifies a benchmark window had no foreign traffic |

## Running

```bash
python3 bench.py Qwen3.6-35B-A3B-4bit --reps 3 --out out.json

# these exact flags reproduce the headline eval numbers
python3 codeeval.py Qwen3.6-35B-A3B-4bit --max-tokens 16000 --temperature 1.0 \
    --extra '{"top_p":0.95,"top_k":20}' --reps 1 --out eval.json

# Qwen3.8 needs its effort pinned or it will not terminate
python3 codeeval.py Qwen3.8-27B-4bit --max-tokens 16000 --temperature 1.0 \
    --extra '{"top_p":0.95,"top_k":20,"chat_template_kwargs":{"reasoning_effort":"medium"}}'

python3 effort.py Qwen3.8-27B-4bit
python3 longctx.py Qwen3.6-35B-A3B-4bit
```

## Measurement protocol — not optional

Three confounds silently produced wrong numbers during this work. Skipping any of these
reproduces them:

1. **Restart oMLX before every measured model.** It keeps every model it has served resident;
   a model measured alongside 69 GB of others read ~30% slow. Restarting once at the *top*
   of a multi-model run is not enough and is an easy mistake to make: the first arm then
   runs alone and every later arm carries the earlier arms' weights. It cost a whole DWQ
   comparison — see `showdown-2026-09-21-CONTAMINATED/WHY-DISCARDED.md`, where the control
   pass came back 22% slower than its own identical first pass. Allow a settle after the
   kickstart, too; it returns before the old process's memory is reclaimed.
2. **Do not compare two models with two sequential passes.** This box heats up under exactly
   the load a benchmark applies: across one 9-minute pass the *same* model read 130.92 then
   110.12 t/s. A 16% session drift cannot rank a 10% difference, and no amount of restarting,
   auditing or re-measuring fixes that — the control can only tell you the answer is
   unusable, which it did, twice. Sample the arms **alternately** instead, flip the order
   each round, and report the median of the paired ratios. `moe_quant_paired.py` is the
   worked example; it survived a 28% drift inside a single pass.
3. **Stamp the window *after* the restart, and audit it.** A scheduled job on the same server
   once depressed a measurement ~20% with nothing in the output to indicate it.
   `contention_audit.sh` fails closed — an unparseable window or empty log is a hard error,
   because a false "CLEAN" launders a bad run as verified.
   ```bash
   printf 'START %s\nEND %s\n' "$(date '+%F %T')" "$(date '+%F %T')" > window.txt
   ./contention_audit.sh window.txt Qwen3.6-35B-A3B-4bit
   ```
4. **Never let the prefix cache serve your prefill.** `longctx.py` defends against this with a
   per-prompt nonce, shuffled sizes, a warm-up, and a `cached_tokens == 0` check. If you write
   a new long-context test, do the same — the tell that we got this wrong originally was a
   4× longer prompt returning *faster*.

Also: this is a live desktop. WindowServer and DisplayLink take a real GPU slice, so absolute
numbers move ±20% between sessions. Trust ratios measured within one pass; re-measure the
first model last to bound the drift.

## Interpreting results

`docs/local-llm-benchmarks.md` has a section defining every metric — what it measures, how it
is computed, and what a high or low score actually means. Read it before quoting a number.
