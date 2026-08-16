# Local LLM model selection — measured on moria

Controlled benchmarks of the local coding models we serve through oMLX, run 2026-08-15 when
Qwen3.8-27B dropped. Covers dense vs MoE, quantization, `reasoning_effort`, speculative
decoding, and long-context prefill.

**This doc is why `dot/omlx/.omlx/model_settings.json` looks the way it does.** The
reproducible harness lives in `dot/omlx/bench/`; the earlier MoE-only speculative-decoding
work is in `dot/omlx/speculative-decoding-findings.md`.

---

## Executive summary

1. **The MoE won. `Qwen3.6-35B-A3B-4bit` is the default coding model** — 130.7 tok/s decode
   vs the dense `Qwen3.8-27B-4bit`'s 23.0 (**5.7×**), and it scored **9/10 vs 8/10** on an
   executable coding eval. Faster *and* not worse, so there is no trade to agonise over.
2. **The newer, higher-benchmarked dense model is the slow specialist.** Qwen3.8-27B is a
   newer generation with better published scores, but we could not measure a quality
   advantage — our eval hits a ceiling. Its real edge is **token efficiency**: it solved the
   eval with 31.8k tokens vs A3B's 84.1k (2.6× fewer).
3. **On a *dense* model, 8-bit costs ~2× the speed for nothing.** 23.0 → 11.9 tok/s. On a
   *MoE* it costs only 1.50× (130.7 → 86.9), because a MoE only reads its ~3B active params.
   The "I have 128 GB so take the 8-bit" instinct is wrong on both, and *most* wrong on dense.
   No 6-bit exists for these models.
4. **Qwen3.8-27B is a retrain on the identical Qwen3.6-27B skeleton** — same config,
   byte-identical 14.95 GiB weights, same measured speed. Free upgrade, old one deleted.
5. **Qwen3.8's `reasoning_effort` defaults to `xhigh`, which is unusable.** Unconfigured it
   burned 8,000 tokens over 401 s and *never produced an answer*. Worse, **more thinking made
   it worse**: `medium` scored 8/10 in 27 min; `xhigh` scored 6/10 in 111 min.
6. **Speculative decoding finally pays off on a dense model (1.43× on code) — but oMLX's
   implementation is not bit-identical**, verified against a determinism control. Left off.
7. **Prefill, not decode, is what you wait for** — and it is where the MoE's lead is widest:
   a 64K context costs A3B 64 s versus the dense model's 291 s.

**Practical rule:** default to A3B-4bit. Reach for Qwen3.8-27B-4bit only when A3B has
actually failed a specific hard problem, or when output tokens are precious. Expect to wait
~5.7× longer when you do.

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

## Test parameters

| test | parameters |
|---|---|
| **Throughput** | temperature 0 (greedy), 200 completion tokens, 3 reps, **median** reported. Three prompt families: code (458 prompt tok), prose (182), qa (179). `decode = completion_tokens / (wall − TTFT)` |
| **Coding eval** | 10 original tasks (written fresh, not HumanEval/MBPP) each with a hidden executable test suite; pass = every assertion holds. temp 1.0 / top_p 0.95 / top_k 20, `max_tokens` 16000, 1 rep per task |
| **Long-context** | thinking disabled, output capped at 24 tokens so wall ≈ prefill. Synthetic source-like prompt repeated to length |
| **reasoning_effort** | one fixed debugging question, temp 1.0 / top_p 0.95 / top_k 20, `max_tokens` 8000 |
| **Speculative decoding** | matched A/B on one server instance, temp 0, 200 tokens, 3 reps |
| **Losslessness** | temp 0, 3 fixed prompts, SHA-256 of `reasoning_content` + `content`, drafter off vs on, **plus a control** (off vs off across a restart) |

**Protocol.** oMLX is restarted before *every* measured model so exactly one is resident, and
each window is audited against the server log for foreign traffic. Both of those controls
exist because skipping them produced wrong numbers — see the confounds section.

---

## Results: throughput

Decode is the sustained generation rate; TTFT is time-to-first-token on the 458-token code
prompt.

| model | type | active params | quant | on disk | **decode tok/s** | TTFT |
|---|---|---|---|---|---|---|
| **Qwen3.6-35B-A3B-4bit** | MoE | ~3B | 4-bit | 19 GB | **130.73** | 0.50 s |
| Qwen3.6-35B-A3B-8bit | MoE | ~3B | 8-bit | 35 GB | 86.91 | 0.54 s |
| Qwen3.6-27B-4bit | dense | 27B | 4-bit | 14.95 GiB | 24.01 | 2.51 s |
| **Qwen3.8-27B-4bit** | dense | 27B | 4-bit | 14.95 GiB | **22.96** | 2.58 s |
| Qwen3.6-27B-8bit | dense | 27B | 8-bit | 27.48 GiB | 11.98 | 2.78 s |
| Qwen3.8-27B-8bit | dense | 27B | 8-bit | 27.48 GiB | 11.93 | 2.34 s |

Per-family medians for the two finalists:

| model | code | prose | qa | avg |
|---|---|---|---|---|
| Qwen3.6-35B-A3B-4bit | 132.61 | 130.66 | 128.92 | **130.73** |
| Qwen3.8-27B-4bit | 23.86 | 22.91 | 22.11 | **22.96** |

**Quantization cost, by architecture:**

| architecture | 4-bit | 8-bit | penalty |
|---|---|---|---|
| dense 27B (Qwen3.8) | 22.96 | 11.93 | **1.92×** |
| dense 27B (Qwen3.6) | 24.01 | 11.98 | **2.00×** |
| MoE 35B-A3B (Qwen3.6) | 130.73 | 86.91 | **1.50×** |

A dense model re-reads every parameter each decode step, so time tracks weight bytes (ratio
27.48/14.95 = 1.84; the excess is KV-cache and activation traffic that doesn't shrink). A MoE
reads only its active experts, so 8-bit hurts less — but it still is not free, which is the
part people get wrong.

## Results: coding eval

10 original tasks, executable tests. Four of the ten suites were validated against reference
solutions first, so a failure means the model got it wrong, not that the harness is broken.

| model | config | **pass** | truncated | tokens | wall-clock | effective tok/s |
|---|---|---|---|---|---|---|
| **Qwen3.6-35B-A3B-4bit** | temp 1.0 | **9/10** | 1 | 84,062 | **17.4 min** | 80.6 |
| Qwen3.8-27B-4bit | `reasoning_effort: medium` | 8/10 | 1 | 31,849 | 27.1 min | 19.6 |
| Qwen3.6-27B-4bit | default (no effort knob) | 8/10 | 3 | 105,207 | 90.7 min | 19.3 |
| Qwen3.8-27B-4bit | `reasoning_effort: xhigh` | 6/10 | 4 | 123,418 | 111.5 min | 18.4 |

Each model is shown at the best configuration found for it. The MoE finishes the whole suite
in 17 minutes; the dense model's best run takes 27, and its *maximum-effort* run takes 111
minutes to score two points lower.

**Read the quality column carefully.** 9-vs-8 on ten tasks is one task — that is noise, not a
demonstrated quality difference, and both are near the ceiling of this eval, which is exactly
when a benchmark stops discriminating. The honest claim is *"the MoE was not worse"*, not
*"the MoE is better"*. The **5.7× speed difference is not noise.**

The 8-vs-6 gap between `medium` and `xhigh` **on the same model and same tasks** is much
better founded, because the failure mode is mechanical and identifiable (truncation).

## Results: `reasoning_effort` (Qwen3.8 only — new in 3.8, absent in 3.6)

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

Practical ordering on this hardware: **`medium` > `low` ≫ `xhigh` (the shipped default)**.

## Results: long-context prefill

For an agent, felt latency is usually prefill — you send a big context and wait. Decode tok/s
says nothing about it. This is where the MoE's advantage is widest.

| prompt tokens | A3B-4bit wall | A3B tok/s | Qwen3.8-27B-4bit wall | dense tok/s | **speedup** |
|---|---|---|---|---|---|
| 1,946 | 7.1 s | 273 | 15.5 s | 125 | 2.2× |
| 7,862 | 5.4 s | 1,451 | 48.8 s | 161 | 9.0× |
| 15,866 | 10.4 s | 1,532 | 63.5 s | 250 | 6.1× |
| 31,874 | 24.2 s | 1,320 | 127.7 s | 250 | 5.3× |
| 63,890 | 64.2 s | 995 | 290.6 s | 220 | 4.5× |

Both scale roughly **linearly**, not quadratically — the hybrid attention doing its job, since
only 16 of 64 (dense) / 10 of 40 (MoE) layers keep a real KV cache. But the dense model's
absolute rate is low enough to hurt: a 32K context costs ~2 minutes before the first token.

Mitigated in practice by prefix caching — this server's own stats show 1,392,640 cached of
1,927,616 prompt tokens, a **72% hit rate**. First turn on a big context is expensive;
follow-ups are not.

## Results: speculative decoding

Previously benchmarked here and **rejected**: a Gemma-4 26B-A4B drafter measured 0.97× on
this machine and 0.91× on an M3 Pro — a net loss, because a ~4B-active MoE isn't
memory-bandwidth-bound on Apple Silicon so a drafter has nothing to recover.

A dense 27B is the opposite regime, and Qwen3.8 ships MTP heads. Re-tested with oMLX
`vlm_mtp` + the 239 MB `Qwen3.8-27B-MTP-4bit` drafter:

| prompt | drafter OFF | drafter ON | speedup | acceptance |
|---|---|---|---|---|
| code | 23.05 | **32.91** | **1.43×** | 63.6% (2.27 tok/round) |
| prose | 23.69 | 25.37 | 1.07× | 50.5% (2.01) |
| qa | 23.78 | 25.95 | 1.09× | 43.0% (1.86) |

**Then the catch.** Greedy verification is supposed to make this *bit-identical*. Tested
rather than assumed:

| run | result |
|---|---|
| **control**: drafter OFF, captured twice across a restart | **3/3 identical** |
| drafter OFF vs drafter ON | **1/3 identical — 2 prompts diverged** |

The control is what makes it conclusive: the server *is* deterministic at temperature 0,
reproducing identical hashes even across a restart. So the divergence is real. **Left
disabled** — a 1.43× speedup that silently changes output is not the trade the technique
advertises.

[mlx-dspark](https://github.com/ARahim3/mlx-dspark) was also evaluated (code 1.55×, math
1.47×, chat 1.15×). Better *ratios*, but from a ~16 tok/s baseline vs oMLX's ~23, so its
accelerated 24.9 tok/s still loses to oMLX+MTP's 32.9 — and it means a second server. Not
adopted.

---

## The part worth blogging: confounds that produced wrong numbers

Every one of these silently produced a plausible, wrong result.

**1. Foreign traffic on a shared server.** A scheduled digest job (normally 05:30, fired late
as a launchd wake catch-up) hammered a *different* model on the same inference server for ~5
minutes. It overlapped exactly one model's window and depressed that measurement ~20% —
11.7 vs 14.6 tok/s. Nothing in the benchmark output hinted at it. Fix: a script that audits a
time window against the server log and refuses to certify a run that shared the GPU.

**2. Engine-pool residency.** oMLX keeps every model it has served resident. With four models
/ 69 GB loaded and free memory at 38%, Qwen3.8-27B-4bit measured **32% slower** than
Qwen3.6-27B-4bit — a difference that would have been written up as a real regression. Measured
alone, they are within 4%, exactly as byte-identical weights predict. Fix: restart the server
before every model.

**3. Ambient desktop load.** WindowServer and DisplayLink take a real GPU slice. To bound it,
each pass re-measures its *first* model *last*: drift across the full matrix came out at
**−3.9%** — an order of magnitude too small to manufacture the 2× quant gap, so the ratios
stand.

**4. Chunk counts are not token counts.** The streaming API packs several tokens per SSE
chunk. Counting chunks produced a nonsensical "7 tok/s decode" against a 22 tok/s end-to-end
rate. Derive decode from `usage.completion_tokens` and TTFT.

**5. Unequal thinking budgets masquerading as a quality gap.** The first quality comparison
gave Qwen3.6-27B 2.9× the token budget of Qwen3.8 (9,251 vs 3,185 tokens/task) purely because
one model has a `reasoning_effort` knob and the other doesn't. That is an *efficiency*
comparison; reporting it as a quality one would simply have been wrong.

**6. Truncation is not failure.** Qwen3.6's `path_normalize` run hit the token cap and still
passed, because the fenced code block landed before the cutoff. Track `finish_reason`
separately from pass/fail or you will conflate "ran out of room" with "got it wrong".

**7. `timeout` does not exist on macOS.** A guard using it silently *skipped* an entire
benchmark phase rather than running it (`gtimeout` from coreutils is the equivalent).

---

## Outcome / current config

- **Default:** `Qwen3.6-35B-A3B-4bit`, temp 0.6 / top_p 0.95 / top_k 20, 8192-token thinking
  budget (its only runaway guard — no `reasoning_effort` knob exists in 3.6). Registered in
  `dot/pi/.pi/agent/models.json.tpl`.
- **Specialist:** `Qwen3.8-27B-4bit`, temp 1.0 / top_p 0.95 / top_k 20,
  `reasoning_effort: medium`, 8192-token budget. For hard problems and token-tight work.
- Speculative decoding **off** pending the losslessness bug.
- Deleted: `Qwen3.6-27B-4bit`, `Qwen3.6-27B-8bit`, `Qwen3.8-27B-8bit`, DSpark drafter — ~73 GB.

## Open questions

- **The eval ceilings out.** 9/10 and 8/10 cannot separate these models. A harder suite (or
  several reps per task, since these are single samples at temperature 1.0) would be needed to
  test whether Qwen3.8's stronger published scores (SWE-bench Pro 61.7, LiveCodeBench v6 90.3,
  Terminal-Bench 2.1 73.0) show up on real work.
- **Is oMLX's `vlm_mtp` divergence a bug?** Worth reporting upstream; re-check after upgrades.
- **Vision untested.** Both models are VLMs; only text was ever sent.

## Links

- [Qwen3.8-27B model card](https://huggingface.co/Qwen/Qwen3.8-27B) · [mlx 4-bit](https://huggingface.co/mlx-community/Qwen3.8-27B-4bit) · [MTP drafter](https://huggingface.co/mlx-community/Qwen3.8-27B-MTP-4bit)
- [Qwen3.6-35B-A3B mlx 4-bit](https://huggingface.co/mlx-community/Qwen3.6-35B-A3B-4bit)
- [mlx-dspark](https://github.com/ARahim3/mlx-dspark) · [DSpark drafter](https://huggingface.co/RadixArk/Qwen3.8-27B-DSpark)
- [Quesma: do Qwen3.6 27B quantizations break the pelican?](https://quesma.com/blog/qwen-quantization-quality/)
- [Speculative decoding (Leviathan et al., ICML 2023)](https://arxiv.org/abs/2211.17192)
