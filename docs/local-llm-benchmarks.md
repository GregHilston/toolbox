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
   The "I have 128 GB so take the 8-bit" instinct is wrong on both. No 6-bit MLX quant is
   published for either model. Tool calling survives the 4-bit quant too — see "Results:
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
anything tested) but 103.6 tok/s vs 130.7 — a 21% speed cost.** By our own n=10 standard the
extra task is not a demonstrated quality gain, while the 21% is measured and certain. Kept on
disk and documented as the quality-leaning alternative; **not made the default.** The slowdown
has a clear cause: DWQ keeps embeddings, `lm_head`, routers and shared experts at higher
precision, and in a MoE those are read on *every* token.

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

Every one of these produced a plausible, wrong result. Three needed permanent tooling.

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

Drift control: each pass re-measures its first model last. Across the full matrix that came
out at **−3.9%** — an order of magnitude too small to manufacture the 2× quant gap.

---

## Outcome / current config

- **Default:** `Qwen3.6-35B-A3B-4bit` — temp 0.6 / top_p 0.95 / top_k 20 / min_p 0.0, with an
  8192-token thinking budget as its only runaway guard (no `reasoning_effort` knob exists in
  Qwen3.6).
- **Specialist:** `Qwen3.8-27B-4bit` — temp 1.0 / top_p 0.95 / top_k 20 / min_p 0.0,
  `reasoning_effort: medium`, 8192-token budget.
- **Quality-leaning alternative, on disk, not default:** `Qwen3.6-35B-A3B-4bit-DWQ`
  (10/10 but 21% slower).
- Speculative decoding **off** pending the losslessness bug.
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
- **Is oMLX's `vlm_mtp` divergence a bug?** Worth reporting upstream; re-check after upgrades
  with `bench/lossless_check.py`.
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
