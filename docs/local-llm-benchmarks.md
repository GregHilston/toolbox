# Local LLM model selection — measured on moria

Controlled benchmarks of the local coding models we serve through oMLX, run 2026-08-15 when
Qwen3.8-27B dropped. Covers dense vs MoE, quantization, `reasoning_effort`, speculative
decoding, and long-context prefill.

**This doc is why `dot/omlx/.omlx/model_settings.json` looks the way it does.** The
reproducible harness lives in `dot/omlx/bench/`; the earlier MoE-only speculative-decoding
work is in `dot/omlx/speculative-decoding-findings.md`.

## Executive summary

1. **The MoE won. `Qwen3.6-35B-A3B-4bit` is the default coding model** — 130.7 tok/s decode
   vs the dense `Qwen3.8-27B-4bit`'s 23.0 (**5.7×**), 6.6–10.0× faster prefill, and it scored
   **9/10 vs 8/10** on an executable coding eval. Faster *and* not worse.
2. **The newer, higher-benchmarked dense model is the slow specialist.** Qwen3.8-27B is a
   newer generation with better published scores, but we could not measure a quality
   advantage — our eval ceilings out. Its real edge is **token efficiency**: 31.8k tokens vs
   A3B's 84.1k to solve the same suite (2.6× fewer).
3. **On a *dense* model, 8-bit costs ~2× the speed for nothing.** 23.0 → 11.9 tok/s. On the
   *MoE* it costs 1.50× (130.7 → 86.9), because a MoE only reads its ~3B active params.
   The "I have 128 GB so take the 8-bit" instinct is wrong on both. (6-bit builds do exist,
   from lmstudio-community; the A3B 6-bit was measured on 2026-10-02 and did not help.) Tool calling survives the 4-bit quant too — see "Results:
   tool calling at 4-bit" — so there is no agentic-use exception to this rule either.
4. **Qwen3.8-27B is a retrain on the Qwen3.6-27B skeleton** — same architecture config,
   identically-sized 14.95 GiB weights, same measured speed. Free upgrade, old one deleted.
5. **Qwen3.8's `reasoning_effort` defaults to `xhigh`, which never terminates.** Unconfigured
   it burned 8,000 tokens over 401 s and produced no answer at all. `medium` scored 8/10 in
   27 min; `xhigh` scored 6/10 in 111 min — every extra failure was a truncation.
6. **Speculative decoding finally pays off on a dense model (1.43× on code) — but oMLX's
   implementation is not bit-identical** against a determinism control. Left disabled.
7. **Prefill, not decode, is what you wait for**, and it is where the MoE's lead is widest
   (6.6–10.0× vs 5.7× on decode). A 64K context costs the dense model **8.5 minutes** to
   first token, versus 77 seconds for the MoE.

**Practical rule:** default to A3B-4bit. Reach for Qwen3.8-27B-4bit only when A3B has actually
failed a specific hard problem, or when output tokens are precious. Expect ~5.7× the wait.

**Superseded on 2026-10-02 for the specialist slot** — see the next section. The default is
unchanged.

---

## 2026-10-02: Swift 1.5, Qwen3.8-Flash-Next, and the A3B 6-bit

oMLX 0.7.0rc1. Question: which Qwen3.8-27B variant and quant is best on moria, is there a
newer Qwen that beats `Qwen3.6-35B-A3B-4bit`, and does a dense model earn a place in reserve.

### The eval

A harder, agentic-shaped task than `codeeval.py`, which had hit its ceiling: the model writes a
one-table CRUD app — Node + SQLite API, React + Vite UI — as files in one reply. The model runs
nothing; `dot/omlx/bench/crud/crud_eval.py` installs it, starts it, and scores **16 checks**:
server starts, the five endpoints, 400 on a missing title/author, 404 on an unknown id,
persistence across a restart, the client build, and five headless-browser UI checks
(list, create, toggle read, edit, delete). I chose SQLite; the prompt names Node 26.

**Hints** are the grader's own failure report, sent back verbatim as the next user turn, at most
two. Every one is saved as `results/<arm>/hints-round-N.md`. No hand-written hints were given.
The one that recurs: nearly every model's first try pins a `better-sqlite3` that cannot build on
Node 26 (it needs 13.x) — a training-cutoff trap, not a compiler problem (verified with clang
forced). So "first try" scores are mostly 1/16, and **what discriminates is whether the model
recovers from the error**. Each model ran with its vendor's recommended sampling; Qwen3.8-family
models with `reasoning_effort: medium`. **The thinking budgets were not equal:** the A3B
entries cap thinking at 8192 tokens, the Qwen3.8-family entries at 16384, so part of the
dense model's lead may be test-time compute. Each run's `summary.json` now records the
settings it was served with; equalise budgets when a comparison hinges on it.

The pi agent loop was not used: an unattended pi worker needs `yoloMode`, which the session's
safety policy blocked. Tool calling was checked separately (below).

### Results (n = runs; full table: `python3 dot/omlx/bench/crud/summarize.py`)

| model | runs | 16/16 at the end | 16/16 with no hints | median gen time | decode tok/s | resident |
|---|---|---|---|---|---|---|
| `Qwen3.6-35B-A3B-4bit` (default) | 3 | 1 | 0 | 3.4 min | 112 | 21 GB |
| `Qwen3.6-35B-A3B-MLX-6bit` | 2 | 1 | 0 | 4.2 min | 90 | 28 GB |
| `Qwen3.8-27B-oQ4e-mtp` (base, MTP off) | 2 | 2 | 1 | 7.6 min | 19 | 16 GB |
| `Swift-1.5-…-oQ4e-mtp`, MTP off | 3 | 3 | 1 | 7.9 min | 20 | 16 GB |
| **`Swift-1.5-…-oQ4e-mtp`, MTP on** | 3 | **3** | **2** | **3.4 min** | **38** | 16 GB |
| `Swift-1.5-…-oQ5e-bf16-mtp` | 1 | 1 | 0 | 11.2 min | 15 | 20 GB |
| `Swift-1.5-…-oQ6e-bf16-mtp` | 1 | 1 | 0 | 9.7 min | 13 | 24 GB |
| `Qwen3.8-Flash-Next-REAP-288-MLX-4bit` | 3 | 2 | 1 | 4.1 min | 47 | 69 GB |

Swap stayed at 0 MB for every moria run. The A3B's failures were real bugs, not grader artefacts:
`lastID` on sql.js (which has none), a wasm file loaded from a CDN URL through `fs`, `require`
of an undeclared dependency, a wrong 404 path. One Flash-Next run went 1 → 10 → 1, rewriting
what worked in a 19.5k-token final attempt.

### Findings

1. **The dense 27B is the reliable one: 10 of 10 runs correct by the end, every quant.** The
   A3B, at either bit-width, finished correct in 2 of 5. Each arm is n ≤ 3, but the gap
   (10/10 vs 2/5) is the one result here that is not noise.
2. **Swift 1.5 over base Qwen3.8: same correctness on this task, better published coding.**
   We could not separate them (2/2 vs 3/3, ~8k tokens each). The case for Swift is ukisai's
   published LiveCodeBench v6 81.7 vs 76.8 and Terminal-Bench 2.1 72.1 vs 69.2, and that it
   costs nothing extra. Licence: free for personal use and for organisations under US$1M
   revenue.
3. **Quant: oQ4e. Higher bits cost speed and bought nothing.** oQ5e and oQ6e (both bf16 for
   sensitive tensors) decoded 26–36% slower than oQ4e and were no more correct. oQ4e is oMLX's own mixed
   4/5-bit imatrix quant and carries the MTP head.
4. **Lightning MTP (`mtp_enabled`) is now worth it: 1.90× decode** (median paired ratio over
   12 alternating pairs, 18.6 → 37.3 tok/s, 77–94% acceptance; `bench/mtp_paired.py`). The
   08-24 "parking" problem (`docs/mtplx-vs-omlx.md`) is gone in 0.7.0rc1: 5–7k-token
   generations held 3.6–4.0 tokens per verify cycle to `finish=stop`. **Still not
   bit-identical** — 0/3 greedy prompts matched, forking at a near-tie (`Optional` vs
   `Union`) with both continuations sound. Taken anyway, because quality with it on was the
   best of any arm (3/3, 2 with no hints).
5. **Prefill has not improved, and it is the dense model's real cost.** Swift oQ4e:
   149–183 tok/s up to 16K, 129 at 64K (8.3 min to first token). A3B: 1,000–1,160 tok/s,
   85 s at 64K. Flash-Next: 450–490 up to 32K, 358 at 64K (3 min). pi's ~7k-token system
   prompt costs the 27B ~45 s cold; the prefix cache makes later turns cheap.
6. **Newer Qwen: there is no Qwen3.8 35B-A3B.** Qwen's 3.8 open weights are the 27B,
   Flash-Next (125B + 51B n-gram embedding, 6B active) and a 2.4T. Flash-Next's full 4-bit is
   111.5 GB, too big for this box without swap; the REAP-288 expert-pruned build (69 GB) runs,
   decodes at 47 tok/s, and was not more reliable than Swift at 4× the memory. Not adopted;
   weights deleted (`sh0wie/Qwen3.8-Flash-Next-REAP-288-MLX-4bit` to re-test).
   `Qwen/Qwen-AgentWorld-35B-A3B` is an environment simulator, not an assistant.
7. **The A3B 6-bit is not an upgrade.** 16% slower than 4-bit, 1 of 2 runs correct.

**Practical rule now:** A3B-4bit stays the default for interactive work — 3× the decode and
7× the prefill, which is what an agent turn over a large context waits on. On this
self-contained task Swift with MTP finished in about the same wall time (3.4 vs 3.1–4.7 min) and was
right far more often, so the A3B's lead is in turn latency, not time-to-correct. **`Swift-1.5-Qwen3.8-27b-oQ4e-mtp` (MTP on) replaces
`Qwen3.8-27B-4bit` as the specialist**, and is the one to pick for any multi-file build where a
wrong answer costs more than a few minutes. Swift + A3B together are 37 GB resident.

**Rejected builds, deleted from disk:** Swift oQ5e/oQ6e
(`dicksondickson/Swift-1.5-Qwen3.8-27b-oQ{5,6}e-bf16-mtp-MLX`), the A3B 6-bit
(`lmstudio-community/Qwen3.6-35B-A3B-MLX-6bit`), Flash-Next REAP. ukisai's own
`Swift-1.5-{4,5}bit-MLX` need a patched mlx-lm and their own server, so they cannot load in oMLX.

**Shell gotcha found on the way:** `pi -p --model …` seemed to ignore `--model`, but pi
was never told. The runs went through `timeout`, and moria's `~/.local/bin/timeout` is a
hand-written wrapper that drops every flag *and the argument after it* — `timeout 60 pi -p
--model X hi` runs `pi X hi`, two prompts on the default model. Sniffing the request body
shows pi 0.87.1 and 1.0.0 both honour `--model` when called directly. Nix now installs GNU
`timeout` on every Mac (`nixos/modules/darwin/home.nix`), which beats `/usr/local/bin`'s
copy on PATH; the `~/.local/bin` one, which beat it, was renamed `timeout.broken-wrapper`.

---

## Test machine

| | |
|---|---|
| Machine | MacBook Pro (Mac16,6), "moria" |
| Chip | Apple M4 Max |
| CPU | 16 cores (12 performance + 4 efficiency) |
| GPU | 40 cores |
| Memory | 128 GB unified |
| OS | macOS 26.5.2 (25F84) |
| Server | oMLX 0.5.7 |
| Runtime | mlx 0.32.0, mlx-vlm 0.6.3, mlx-lm 0.31.3 |

**This is a live desktop, not a clean bench.** WindowServer (~23–30% CPU) and DisplayLink
(~8%) compete for the GPU. The same model+quant measured 29 tok/s early and 24 tok/s an hour
later. Absolute numbers carry roughly ±20%; only ratios measured within a single pass are
trustworthy. Do not compare these numbers across sessions or against other machines.

---

## What each benchmark measures, how, and how to read it

Every number below is defined here so a high or low score can be interpreted rather than
just compared.

### 1. Decode throughput (tok/s) — *higher is better*

**What:** sustained generation rate once the prompt has been processed — how fast words appear.

**How:** streaming request, 200 completion tokens, temperature 0, 3 repetitions. Computed as
`usage.completion_tokens / (wall − TTFT)`, i.e. tokens divided by the post-prefill span. We
report the **median of 3 runs per prompt family** (code / prose / qa), then the **mean of
those three family medians** as the headline figure.

**Why it matters:** this is the dominant cost for long answers, and for a *dense* model it is
memory-bandwidth-bound — decode time tracks total weight bytes almost exactly. That is the
whole reason quantization choice matters so much on dense models and less on MoE.

**Reading it:** below ~20 tok/s feels sluggish for interactive work (you watch it type);
above ~80 tok/s feels essentially instant. A ratio between two models is far more reliable
than either absolute number on this machine.

**Trap:** oMLX packs several tokens into one SSE chunk, so counting chunks is *not* counting
tokens. Doing that once produced a nonsensical "7 tok/s decode" against a 22 tok/s end-to-end
rate. The harness now hard-fails rather than falling back to chunk counts.

### 2. TTFT — time to first token (seconds) — *lower is better*

**What:** latency from sending the request to the first token appearing. Almost entirely
prefill plus queueing.

**How:** wall time to the first streamed content chunk, from the same runs as decode.

**Why it matters:** this is the pause you *feel* before anything happens. Decode throughput
says nothing about it.

**Reading it:** under ~1 s feels responsive; several seconds on a short prompt signals an
expensive prefill path, and it will scale badly with context.

### 3. Prefill throughput (tok/s) — *higher is better*

**What:** the rate at which the model ingests your prompt.

**How:** measured directly by `longctx.py` — thinking disabled and output capped at 24 tokens
so wall-clock ≈ prefill. Prompt sizes ~2K to ~64K tokens.

**Why it matters:** for agentic coding this dominates everything. You paste a large repo
context and wait. Decode speed is irrelevant until prefill finishes.

**Reading it:** watch both the *rate* and the *shape*. Roughly flat or gently declining with
length is good (attention cost is not blowing up); a collapsing curve means quadratic
behaviour. Both models here scale roughly linearly, which is the hybrid attention working —
only 16 of 64 (dense) and 10 of 40 (MoE) layers keep a real KV cache.

**Trap — this one invalidated our first attempt.** oMLX runs a prefix cache. Building each
prompt as `header + filler×N + question` and walking sizes in ascending order makes every
prompt a strict prefix-extension of the last, so most of the prefill is served from cache.
The tell was unmistakable: a 7,862-token prompt returned *faster* in wall-clock than a
1,946-token one. The harness now puts a unique random nonce in the first line of every
prompt, shuffles the size order, warms up first, and asserts `cached_tokens == 0` on every
row. All prefill figures below are from the corrected run.

### 4. Coding eval pass rate (x/10) — *higher is better, but see the caveat*

**What:** fraction of 10 original coding tasks whose hidden assertion suite passes.

**How:** each task states a precise spec; the model emits a fenced Python block; we `exec` it
and run assertions it never saw. Pass = every assertion holds. No judging, no rubric, no
partial credit. Tasks were written fresh rather than taken from HumanEval/MBPP to limit
training-set contamination, and all ten were validated against reference solutions first, so
a failure means the model got it wrong and not that the harness is broken.

**Why it matters:** it is objective and it tests the thing we actually care about — following
a precise spec and handling edge cases, not producing plausible-looking code.

**Reading it — the important part:** with n=10, **a one-task difference is noise.** 9/10 vs
8/10 establishes "not worse", never "better". Both models here also sit near the ceiling of
this suite, which is precisely when a benchmark stops discriminating. Only a gap of several
tasks would be meaningful, and we do not have one.

### 5. Truncation count — *lower is better*

**What:** how many tasks hit the token cap (`finish_reason: length`) instead of finishing.

**How:** recorded separately from pass/fail, because they mean different things.

**Why it matters:** a truncation is a **configuration** failure, not a capability failure —
the model ran out of room, it did not get the answer wrong. Conflating the two makes a badly
configured model look stupid. Note truncation is not automatically a failure: one run hit the
cap and still passed, because the fenced code block landed before the cutoff.

**Reading it:** high truncation counts mean your `reasoning_effort` / thinking budget is
wrong. That is a knob, not a verdict on the model.

### 6. Tokens spent, and wall-clock for the suite — *lower is better*

**What:** total completion tokens to solve all 10 tasks, and the end-to-end time to do it.

**Why it matters:** tokens measure verbosity; wall-clock measures your actual experience and
combines speed *and* verbosity. A model can be slow per token but terse enough to win, or
fast but so rambling it loses. Wall-clock is arguably the single most honest headline metric.

**Reading it:** only meaningful *alongside* pass rate. Fewer tokens at equal quality is
strictly better; fewer tokens at lower quality is just a worse model.

### 7. Draft acceptance (speculative decoding) — *higher is better*

**What:** the fraction of speculatively drafted tokens the target model accepts, and the mean
tokens emitted per verification round.

**How:** read from oMLX's own `vlm_mtp stats` log lines.

**Why it matters:** it predicts speedup — but **not on its own.** Every rejected token is
wasted verify compute, so acceptance has to be weighed against the cost of the verify pass.
High acceptance on a model whose decode isn't bandwidth-bound still yields no speedup, which
is exactly why this technique lost on our Gemma MoE and wins on the dense 27B.

### 8. Losslessness (hash identity) — *identical is required, not merely desirable*

**What:** whether enabling an optimization changes the output at all.

**How:** SHA-256 over `reasoning_content + content` at temperature 0 for 3 fixed prompts, with
the optimization off vs on — **plus a control**: off vs off, across a server restart.

**Why it matters:** speculative decoding with greedy verification is supposed to be
*bit-identical* to plain decoding. That is the entire appeal: free speed, no quality
question. If output changes, you are silently trading quality for speed and you no longer
know what you are running.

**Reading it:** the control is not optional. Without it you cannot distinguish a real
divergence from ordinary nondeterminism, and a "failed" losslessness test would be
uninterpretable.

### 9. Quantization penalty (ratio) — *lower is better*

**What:** decode speed at 4-bit ÷ decode speed at 8-bit for the same model.

**Why it matters:** it tells you what a quantization level costs *on this architecture*,
which is not a constant. On a dense model it should approximate the weight-byte ratio; on a
MoE it should be smaller, because only the active experts are read per token.

**Reading it:** a penalty near the weight-byte ratio means you are purely bandwidth-bound. A
much smaller penalty (our MoE, 1.50× against a 1.84× byte ratio) confirms the active-parameter
story. It is never *zero*, which is the part people assume wrongly.

---

## Results: throughput

| model | type | active | quant | on disk | **decode tok/s** | TTFT |
|---|---|---|---|---|---|---|
| **Qwen3.6-35B-A3B-4bit** | MoE | ~3B | 4-bit | 19 GB | **130.73** | 0.50 s |
| Qwen3.6-35B-A3B-4bit-DWQ | MoE | ~3B | 4-bit DWQ | 19 GB | 103.64 | 0.52 s |

The DWQ row was measured sequentially and is depressed by session drift; the
checkpoint-to-checkpoint figure is the paired **-9.8%**, not `103.64 / 130.73`.
| Qwen3.6-35B-A3B-8bit | MoE | ~3B | 8-bit | 35 GB | 86.91 | 0.54 s |
| Qwen3.6-27B-4bit | dense | 27B | 4-bit | 14.95 GiB | 24.01 | 2.51 s |
| **Qwen3.8-27B-4bit** | dense | 27B | 4-bit | 14.95 GiB | **22.96** | 2.58 s |
| Qwen3.6-27B-8bit | dense | 27B | 8-bit | 27.48 GiB | 11.98 | 2.78 s |
| Qwen3.8-27B-8bit | dense | 27B | 8-bit | 27.48 GiB | 11.93 | 2.34 s |

Per-family medians for the two finalists:

| model | code | prose | qa | mean |
|---|---|---|---|---|
| Qwen3.6-35B-A3B-4bit | 132.61 | 130.66 | 128.92 | **130.73** |
| Qwen3.8-27B-4bit | 23.86 | 22.91 | 22.11 | **22.96** |

**Quantization penalty by architecture:**

| architecture | 4-bit | 8-bit | penalty | weight-byte ratio |
|---|---|---|---|---|
| dense 27B (Qwen3.8) | 22.96 | 11.93 | **1.92×** | 1.84× |
| dense 27B (Qwen3.6) | 24.01 | 11.98 | **2.00×** | 1.84× |
| MoE 35B-A3B (Qwen3.6) | 130.73 | 86.91 | **1.50×** | 1.84× |

The dense penalty tracks the weight-byte ratio closely (the excess is KV-cache and activation
traffic that does not shrink). The MoE penalty is materially smaller because only the active
experts are read — but it is not free, which is the widely-assumed-wrong part.

## Results: coding eval

| model | config | **pass** | truncated | tokens | wall-clock | effective tok/s |
|---|---|---|---|---|---|---|
| Qwen3.6-35B-A3B-4bit-**DWQ** | temp 1.0 | **10/10** | 1 | 87,777 | 19.1 min | 76.6 |
| **Qwen3.6-35B-A3B-4bit** | temp 1.0 | **9/10** | 1 | 84,062 | **17.4 min** | 80.6 |
| Qwen3.8-27B-4bit | `reasoning_effort: medium` | 8/10 | 1 | 31,849 | 27.1 min | 19.6 |
| Qwen3.6-27B-4bit | default (no effort knob) | 8/10 | 3 | 105,207 | 90.7 min | 19.3 |
| Qwen3.8-27B-4bit | `reasoning_effort: xhigh` | 6/10 | 4 | 123,418 | 111.5 min | 18.4 |

Each model is shown at the best configuration found for it. The MoE finishes the suite in 17
minutes; the dense model's best run takes 27, and its *maximum-effort* run takes 111 minutes
to score two points lower.

**Apply the n=10 caveat consistently.** 9-vs-8 is one task and does not establish a quality
difference — nor does 10-vs-9 for DWQ. What *is* solidly established here is the 5.7× speed
gap, and that unset/`xhigh` **never terminates** (`finish_reason: length` at 401 s and 405 s,
zero characters of `reasoning_content`) at 4× the wall-clock. The `medium`-vs-`xhigh` gap is
two tasks with a mechanistic explanation (truncation), which makes it *suggestive* rather
than proven — but pinning `medium` needs only the non-termination result, which is
unambiguous.

## Results: tool calling at 4-bit (added 2026-09-03)

The question that came up when pi's default was moved from the 8-bit A3B to the 4-bit:
does the lower quant hurt *function calling*, which the coding eval above does not exercise
(it is single-shot completion against executable tests, no tools). Checked two ways.

**Live, through pi against oMLX**, the harness we actually use: one prompt asking for two
tool-driven tasks — count the lines of a file with a tool, then fix a bug in `add()` with the
`edit` tool — run on each quant with the shipped `model_settings.json` sampling.

| model | tool calls made | result | wall-clock | prompt tokens |
|---|---|---|---|---|
| Qwen3.6-35B-A3B-4bit | `bash`, `read`, `edit` | correct fix, correct count | 15 s | 7,533 |
| Qwen3.6-35B-A3B-8bit | `read`, `read`, `edit` | correct fix, correct count | 16 s | 7,498 |

Both produced well-formed tool calls on the first try, chose sensible tools, and made the
one-character fix without collateral edits. n=1 per model, so this is a smoke test, not a
benchmark: it rules out the failure mode where a 4-bit quant emits malformed JSON or stops
calling tools, which is the only one that would have blocked the switch.

**From the published cards.** The A3B 4-bit MLX quants (mlx-community and Unsloth's UD
variant) both note tool-calling parser fixes in their recent revisions; nothing in the model
cards or the r/LocalLLaMA threads found claims a tool-calling regression between 4-bit and
8-bit on this model. The one 4-bit A3B quant with a documented tool-calling failure is the
**OptiQ** mixed-precision build (mlx-community discussion #2), which is not one we serve.

**Read together with the coding eval:** 4-bit scored 9/10 there and the DWQ 4-bit 10/10, so
on this MoE the 4-bit is not a measured quality loss on either axis, and it decodes 1.50×
faster for 19 GB instead of 35 GB. That is why pi and opencode default to it
(`nixos/modules/darwin/home.nix`), matching oMLX's own `is_default`.

## Results: `reasoning_effort` (new in Qwen3.8; absent in Qwen3.6)

The chat template defaults it to `xhigh` (`chat_template.jinja:47`). One debugging question,
8000-token cap:

| reasoning_effort | tokens | wall | think / answer chars | finish |
|---|---|---|---|---|
| *(unset → xhigh)* | 8000 (cap) | 401 s | 0 / 36,487 | `length` — **no answer** |
| `low` | 1,925 | 95 s | 5,940 / 2,119 | clean stop |
| `medium` | 3,589 | 178 s | 10,371 / 3,938 | clean stop |
| `xhigh` (explicit) | 8000 (cap) | 405 s | 0 / 35,896 | `length` — **no answer** |
| `enable_thinking: false` | 848 | 42 s | 0 / 3,444 | clean stop |

Unset and explicit `xhigh` behave identically, confirming the default. A side effect worth
knowing: because `</think>` never arrives, the parser cannot split reasoning from content, so
all ~36k characters land in `content` and `reasoning_content` comes back empty.

## Results: DWQ vs plain 4-bit, measured in pairs

Two sequential attempts at this comparison were thrown out by their own drift controls, and
the lesson generalises to any A-vs-B on this box.

| attempt | design | control said | verdict |
|---|---|---|---|
| 1 | one oMLX restart at the top | plain re-measured **22% slow** | residency: arm 2 carried arm 1's 19 GB |
| 2 | restart before every arm | plain 130.92 -> 110.12 t/s across the pass | **16% thermal drift vs an ~18% effect** |
| 3 | **A/B/A/B, both models warm** | plain drifted 28% and it did not matter | usable |

The fix is not a better control, it is a design where drift cancels. Warm both models so
residency is identical and stable, then sample the two alternately, flipping the order each
round. Every round yields a *paired* ratio taken seconds apart, so a machine sliding under
the pass slides under both halves of every pair. Report the median of the ratios and their
spread — never a difference of two averages taken minutes apart.

| axis | plain | DWQ | paired ratio | DWQ cost |
|---|---|---|---|---|
| decode (n=6 pairs) | 126-134 t/s | 119-121 t/s | median 0.902, spread 0.886-0.953 | **-9.8%** |
| prefill @32K (n=5 pairs) | 867-1248 t/s | 787-1124 t/s | median 0.907, spread 0.836-1.002 | **-9.3%** |

The two axes agreeing at ~10% is the result. The wide absolute ranges in that table are the
drift the pairing absorbed; the ratios are what to read.

**This supersedes the 21%** that the quantization section quoted for a year. That figure came
from sequential passes on a machine that heats up under exactly the load a benchmark applies,
so it measured the session as much as the checkpoint. Reproduce with
`bench/moe_quant_paired.py`.

## Results: long-context prefill (corrected)

**These numbers replace an earlier contaminated set** — see trap #3 above. Every row below was
verified `cached_tokens == 0`.

| prompt tokens | A3B-4bit | A3B tok/s | Qwen3.8-27B-4bit | dense tok/s | **MoE speedup** |
|---|---|---|---|---|---|
| ~2K | 1.97 s | 996 | 14.64 s | 134 | **7.4×** |
| ~8K | 7.19 s | 1,095 | 52.38 s | 150 | **7.3×** |
| ~16K | 10.71 s | 1,483 | 107.57 s | 148 | **10.0×** |
| ~32K | 28.07 s | 1,136 | 224.57 s | 142 | **8.0×** |
| ~64K | 77.20 s | 828 | 508.11 s | 126 | **6.6×** |

Two readings:

- **Prefill is where the MoE's lead is widest** — 6.6–10.0×, against 5.7× on decode. (The
  contaminated data had *understated* this; the corrected data supports the claim the earlier
  draft made for the wrong reason.)
- **The dense model's prefill is punishing in absolute terms.** It holds a near-flat
  126–150 tok/s at every length — linear scaling, which is architecturally good — but the
  rate is low enough that a 64K context costs **8.5 minutes before the first token**. For
  repo-scale context that, not decode, is the thing that makes it unusable.

Mitigated in practice by prefix caching: this server's own stats show 1,392,640 cached of
1,927,616 prompt tokens, a **72% hit rate**. First turn on a big context is expensive;
follow-ups are not. (That same cache is what corrupted the first measurement.)

## Results: speculative decoding

Previously benchmarked and **rejected**: a Gemma-4 26B-A4B drafter measured 0.97× here and
0.91× on an M3 Pro — a net loss, because a ~4B-active MoE is not bandwidth-bound so a drafter
has nothing to recover.

A dense 27B is the opposite regime, and Qwen3.8 ships MTP heads. Re-tested with oMLX
`vlm_mtp` + the 239 MB `Qwen3.8-27B-MTP-4bit` drafter:

| prompt | drafter OFF | drafter ON | speedup | acceptance |
|---|---|---|---|---|
| code | 23.05 | **32.91** | **1.43×** | 63.6% (2.27 tok/round) |
| prose | 23.69 | 25.37 | 1.07× | 50.5% (2.01) |
| qa | 23.78 | 25.95 | 1.09× | 43.0% (1.86) |

**Then the catch.** Greedy verification should be bit-identical. Tested rather than assumed:

| run | result |
|---|---|
| **control** — drafter OFF, captured twice across a restart | **3/3 identical** |
| drafter OFF vs drafter ON | **1/3 identical — 2 prompts diverged** |

The control shows the server is deterministic at temperature 0, reproducing identical hashes
even across a restart — so the divergence is consistent with a real effect of the drafter
rather than nondeterminism. With n=3 this is strong evidence rather than proof, and it looks
like an oMLX 0.5.7 bug. **Left disabled** — a 1.43× speedup that silently changes output is
not the trade the technique advertises.

[mlx-dspark](https://github.com/ARahim3/mlx-dspark) was also evaluated (code 1.55×, math
1.47×, chat 1.15×). Better *ratios*, but from a ~16 tok/s baseline vs oMLX's ~23, so its
accelerated 24.9 tok/s still loses to oMLX+MTP's 32.9 — and it means a second server on port
8080. **Not adopted.**

## Settings research: what we checked for a free win, and what we found

Before locking this in we went looking for settings or checkpoints that would improve quality
or speed at no cost. Most candidates did not survive contact with the numbers.

**Sampling parameters — already correct, verified against the official card.** Qwen publishes
*different* recommendations per task type for Qwen3.6-35B-A3B:

| mode | temp | top_p | top_k | min_p | presence_penalty |
|---|---|---|---|---|---|
| Thinking, general | 1.0 | 0.95 | 20 | 0.0 | **1.5** |
| **Thinking, precise coding** | **0.6** | **0.95** | **20** | **0.0** | **0.0** |
| Non-thinking / instruct | 0.7 | 0.80 | 20 | 0.0 | 1.5 |

Our shipped config (temp 0.6, presence_penalty 0.0) is exactly the **precise-coding** row —
no change needed. The card warns that a higher `presence_penalty` "may occasionally result in
language mixing and a slight decrease in model performance", so the general-purpose 1.5 is
explicitly *not* what you want for code. We added `min_p: 0.0` explicitly to match. Qwen also
recommends an output length of 32,768 tokens for most queries and 81,920 for hard
maths/programming — our pi registry already declares `maxTokens: 81920`.

**DWQ (distilled weight quantization) — real, but not free.** `Qwen3.6-35B-A3B-4bit-DWQ`
gradient-optimizes the quantization scales against a full-precision teacher, and is reported
to behave like ~4.6-bit. Measured here: **10/10 on the coding eval (the best result of
anything tested). **The "21% speed cost" this section carried for a year is about double the
real figure: measured in pairs, DWQ costs 9.8% on decode and 9.3% on prefill.** By our own
n=10 standard the extra task is still not a demonstrated quality gain — but a 10% cost is a
far easier price than 21%, and it is why the unattended agent sandbox runs DWQ deliberately
(`~/Git/notes/ref-long-running-harnesses.md`) while pi keeps the plain build for interactive
work, where 10% is felt and a human is present to catch a bad turn. The slowdown
has a clear cause, though not quite the one written here originally. Read the two
`config.json` quantization blocks side by side and the difference is precision layout, not
learned scales: the plain build is `bits: 4` with 80 modules bumped to 8-bit (the MoE
gates), while the DWQ build is **`bits: 8`** with 240 modules dropped to 4-bit — and those
240 are exactly the expert FFNs. So the DWQ checkpoint runs the embeddings, `lm_head`, the
gates and **the entire attention stack** at 8-bit, and only the experts at 4. The shared
experts are 4-bit in DWQ, not 8-bit as this section used to say. Both land at ~19 GB because
the experts dominate the parameter count; what differs is how much 8-bit weight is touched
per token. Upstream mlx-lm claims DWQ improves quality and makes **no** claim about
inference cost, so the penalty belongs to this checkpoint's layout rather than to DWQ the
method.

**OptiQ — rejected on its own numbers.** `Qwen3.6-35B-A3B-OptiQ-4bit` advertises a higher
aggregate "Capability Score", but the per-metric table shows it **losing** on MMLU (−0.9),
GSM8K (−1.5) and IFEval (−0.4), **tying HumanEval (+0.0)**, and winning only on BFCL-V3
(+2.5) and HashHop (+8.0). The aggregate is carried by long-context retrieval. For coding
specifically it offers nothing, and it is 24.7 GB against our 19 GB.

**TurboQuant KV-cache quantization — do not enable.** oMLX exposes `turboquant_kv_enabled` /
`turboquant_kv_bits`, but 4-bit and 6-bit modes are reported ~8× *slower* than off (a known
regression); only 8-bit improves anything, and the toggle has at times been disabled pending
a prefill-path fix.

---

## Confounds that produced wrong numbers

Every one of these produced a plausible, wrong result. Four needed permanent tooling.

**1. Foreign traffic on a shared server.** Another process on this machine hammered
`gpt-oss-120b` on the same oMLX instance for ~5 minutes — most likely a manual `roger` run,
which uses that model. It overlapped exactly one model's window — `Qwen3.6-27B-8bit`, which
read **11.7 tok/s** contaminated versus **11.98 tok/s** in the final clean run.

(An earlier draft blamed roger's *scheduled* digest agent. That was wrong and is worth
recording as its own lesson: that agent turned out to fail at Redis before ever reaching the
LLM, so it cannot have been the source. A plausible-sounding culprit is not evidence — the
log tells you *which model* was served, never *which process* asked for it.) Nothing in the benchmark output
hinted at it. `bench/contention_audit.sh` now audits a window against the server log, and
**fails closed**: an unparseable window, an unreadable log, or an empty window is a hard
error, because a false "CLEAN" launders a bad run as verified.

**2. Engine-pool residency.** oMLX keeps every model it has served resident. With 4 models /
69 GB loaded and free memory at 38%, Qwen3.8-27B-4bit measured **32% slower** than
Qwen3.6-27B-4bit — which would have been written up as a real regression. Measured alone they
are within 4.4%, as identically-sized weights on an identical architecture predict. Every
measured model now gets a freshly restarted server.

**3. Prefix caching in the long-context test.** Covered in full under benchmark #3 above: a
4× longer prompt returning *faster* was the tell. Fixed with per-prompt nonces, shuffled
order, a warm-up, and an explicit `cached_tokens == 0` assertion.

**4. Chunk counts are not token counts.** The streaming API packs several tokens per SSE
chunk; counting chunks produced a nonsensical "7 tok/s decode" against a 22 tok/s end-to-end
rate. The harness now hard-fails instead of falling back.

**5. Unequal thinking budgets masquerading as a quality gap.** The first quality comparison
gave Qwen3.6-27B far more test-time compute than Qwen3.8 purely because one model has a
`reasoning_effort` knob and the other does not — 10,521 vs 3,185 tokens/task in the final
runs, a 3.3× gap. That is an *efficiency* comparison; reporting it as a quality one would
have been wrong.

**6. Truncation is not failure.** One run hit the token cap and still passed, because the
fenced code block landed before the cutoff. Track `finish_reason` separately from pass/fail.

**7. `timeout` does not exist on macOS.** A guard using it silently *skipped* an entire
benchmark phase rather than running it (`gtimeout`, from coreutils, is the equivalent).

**8. Thermal drift across a sequential A-vs-B.** The confound that cost two whole
comparison runs on 2026-09-21. Restarting the server per model (confound #2) fixes residency
and leaves this one untouched: a benchmark is sustained GPU load, the machine warms under it,
and the *same* model measured at the start and the end of one 9-minute pass read **130.92
then 110.12 tok/s**. A 16% session drift cannot rank a 10% difference between checkpoints,
and the re-measure-first-model-last control can only report that the run is unusable — which
it did, both times. The fix is a design where drift cancels rather than a better control:
warm both models so residency is identical, then sample them **alternately**, flipping the
order each round, and report the median of the *paired* ratios. That design returned a stable
answer through a 28% drift inside its own pass. `bench/moe_quant_paired.py`.

**9. Reading a quantization penalty off two sequential medians.** The corollary, and the
reason the DWQ figure in this document was wrong by roughly 2× for a year. `103.64 / 130.73`
looks like a checkpoint ratio and is really a session ratio. Paired sampling puts DWQ at
**-9.8% decode / -9.3% prefill**, not -21%.

Drift control: each pass re-measures its first model last. Across the 2026-08-15 matrix that
came out at **−3.9%** — an order of magnitude too small to manufacture the 2× quant gap.
**It does not generalise.** On 2026-09-21 the same control read −16% and −28%, on a machine
that had been running agent workloads for the previous hour. Treat −3.9% as one session's
luck, not as this box's drift, and re-read the control every time.

## Outcome / current config

- **Default:** `Qwen3.6-35B-A3B-4bit` — temp 0.6 / top_p 0.95 / top_k 20 / min_p 0.0, with an
  8192-token thinking budget as its only runaway guard (no `reasoning_effort` knob exists in
  Qwen3.6).
- **Specialist:** `Swift-1.5-Qwen3.8-27b-oQ4e-mtp` with `mtp_enabled` since 2026-10-02 (it
  replaced `Qwen3.8-27B-4bit`) — temp 1.0 / top_p 0.95 / top_k 20 / min_p 0.0,
  `reasoning_effort: medium`, 16384-token budget. See the 2026-10-02 section.
- **Quality-leaning alternative, on disk, nothing uses it:** `Qwen3.6-35B-A3B-4bit-DWQ`
  (10/10, and ~10% slower — not the 21% long quoted here).
- Speculative decoding **on for the specialist only**, taken knowingly: not bit-identical,
  quality held (2026-10-02 section).
- Deleted: `Qwen3.6-27B-4bit`, `Qwen3.6-27B-8bit`, `Qwen3.8-27B-8bit`, DSpark drafter (~73 GB).

Two honest notes on the shipped config: the headline 9/10 was measured at temp **1.0** and
with a 16k ceiling, whereas we ship temp 0.6 (the official coding recommendation) and an 8192
thinking budget. The budget is deliberately tighter than the ceiling that produced the score —
it is a guard against the runaway case, and it reserves room for the answer rather than
capping total output.

## Open questions

- **The eval ceilings out.** 10/10, 9/10 and 8/10 cannot separate these models. A harder suite,
  and several repetitions per task (these are single samples at temperature 1.0), would be
  needed to test whether Qwen3.8's stronger published scores (SWE-bench Pro 61.7,
  LiveCodeBench v6 90.3, Terminal-Bench 2.1 73.0) show up on real work.
- **Is oMLX's MTP divergence a bug?** It persists in 0.7.0rc1's Lightning MTP; re-check after
  upgrades with `bench/mtp_paired.py`.
- **DWQ deserves a proper test** — a bigger suite would say whether that 10/10 is real.
- **Vision untested.** Both models are VLMs; only text was ever sent.

## Reproduction

The harness is checked in at **`dot/omlx/bench/`**. It reads the oMLX API key from
`$OMLX_API_KEY`, or from a gitignored `omlx_key` file beside the scripts.

```bash
cd ~/Git/toolbox/dot/omlx/bench
export OMLX_API_KEY=$(python3 -c "import json,os;print(json.load(
  open(os.path.expanduser('~/.omlx/settings.json')))['auth']['api_key'])")

# 1. decode/prefill throughput -- 3 reps, code/prose/qa, median per family
python3 bench.py Qwen3.6-35B-A3B-4bit --reps 3 --out out.json

# 2. reasoning_effort cost per level (Qwen3.8 only; 3.6 has no such knob)
python3 effort.py Qwen3.8-27B-4bit

# 3. long-context prefill -- nonce'd + shuffled so the prefix cache cannot help
python3 longctx.py Qwen3.6-35B-A3B-4bit

# 4. coding eval: 10 original tasks with executable tests.
#    These exact flags reproduce the headline numbers.
python3 codeeval.py Qwen3.6-35B-A3B-4bit --max-tokens 16000 --temperature 1.0 \
    --extra '{"top_p":0.95,"top_k":20}' --reps 1 --out eval.json
#    Qwen3.8 additionally needs its effort pinned, or it will not terminate:
python3 codeeval.py Qwen3.8-27B-4bit --max-tokens 16000 --temperature 1.0 \
    --extra '{"top_p":0.95,"top_k":20,"chat_template_kwargs":{"reasoning_effort":"medium"}}'

# 5. losslessness: capture off, enable the drafter, capture, compare -- and run the
#    off-vs-off control, without which a divergence is uninterpretable
python3 lossless_check.py Qwen3.8-27B-4bit off
#    ...enable vlm_mtp in model_settings.json, restart oMLX...
python3 lossless_check.py Qwen3.8-27B-4bit on
python3 lossless_check.py --compare off on

# 6. certify a window had no foreign traffic (fails closed)
./contention_audit.sh window.txt Qwen3.6-35B-A3B-4bit
```

**Measure one model per oMLX restart**, stamp the window *after* the restart, and always run
`contention_audit.sh` afterwards. A model measured alongside 69 GB of other resident models
reads ~30% slow.

## Links

- [Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) · [mlx 4-bit](https://huggingface.co/mlx-community/Qwen3.8-27B-4bit) · [MTP drafter](https://huggingface.co/mlx-community/Qwen3.8-27B-MTP-4bit)
- [Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · [mlx 4-bit](https://huggingface.co/mlx-community/Qwen3.6-35B-A3B-4bit) · [4-bit DWQ](https://huggingface.co/mlx-community/Qwen3.6-35B-A3B-4bit-DWQ) · [OptiQ 4-bit](https://huggingface.co/mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit)
- [mlx-lm learned quants (DWQ)](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/LEARNED_QUANTS.md)
- [mlx-dspark](https://github.com/ARahim3/mlx-dspark) · [DSpark drafter](https://huggingface.co/RadixArk/Qwen3.8-27B-DSpark)
- [Quesma: do Qwen3.6 27B quantizations break the pelican?](https://quesma.com/blog/qwen-quantization-quality/)
- [Speculative decoding (Leviathan et al., ICML 2023)](https://arxiv.org/abs/2211.17192)
