# MTPLX vs oMLX for Qwen3.8-27B — measured on moria

Prompted by [this r/LocalLLaMA benchmark post](https://www.reddit.com/r/LocalLLaMA/comments/1vwbyzr/benchmark_results_what_is_the_best_and_fastest/)
(u/ex-arman68), which ranks **MTPLX** above **oMLX** for running Qwen3.8-27B on macOS.
Run 2026-08-24. Companion to `local-llm-benchmarks.md`, which owns model selection;
this doc owns the **engine** question only.

## Executive summary

1. **The post's ranking does not reproduce on moria.** Head to head at 4-bit, each engine
   running its own vendor-recommended fused-MTP checkpoint, burst decode was
   **MTPLX 47.7 t/s vs oMLX 45.8 t/s** — a 3.9% gap, inside this machine's ±20% noise.
2. **But MTPLX does win on sustained long generation — 34.3 vs 22.8 t/s (1.51×)** — and
   the cause is not speculation quality. It is an oMLX **parking** behaviour (§4).
3. **The single biggest win is available without adopting MTPLX at all.** Our current
   production config for this model measured **20.1 t/s**. Simply switching to the fused
   `Qwen3.8-27B-oQ4e-mtp` checkpoint with oMLX's native `mtp_enabled` gives **45.8 t/s
   burst / 22.8 t/s sustained** on the server we already run.
4. **Neither engine's speculation is bit-lossless.** Both scored 3/3 on a determinism
   control and 2/3 with speculation on. This *revises* `local-llm-benchmarks.md`, which
   recorded the divergence as a suspected oMLX 0.5.7 bug.
5. **Prefill is a tie and neither engine helps it.** 127–159 t/s (MTPLX) against oMLX's
   already-documented 126–150. The post's "oMLX has the slowest prefill by far" does not
   hold on M4 Max — as its own author predicted it might not.

**Recommendation: adopt `Qwen3.8-27B-oQ4e-mtp` + `mtp_enabled` in oMLX. Do not adopt
MTPLX.** Rationale in §6.

---

## 1. Why the post's numbers do not transfer

Three reasons, all verifiable in the thread or on the model cards:

| Issue | Detail |
|---|---|
| **The author retracted the oMLX rows** | In-thread: *"Hold on until I re-run the omlx tests. I made a mistake."* Every oMLX number in that table is self-flagged as suspect. |
| **M2 Max, not M4/M5** | The post says outright that oMLX's prefill claim "might be true on newer M4 and M5 chips, but definitely not on the M2 I used." moria is M4 Max. |
| **8-bit, which we do not run** | `local-llm-benchmarks.md` measured 8-bit costing ~2× decode on a dense 27B for no detectable quality gain. |

And MTPLX's own model card concedes the 4-bit case:

> "For context on the same night and the same task: … **oMLX 0.5.7 with its own Qwen 3.8
> 4-bit MTP quant ran 63.3 tok/s.** MTPLX Bare Speed ran 65.2 on that task; this build
> [58.7] gives up a few tok/s to be much closer to the original model."

## 2. What our own benchmark doc had missed

`local-llm-benchmarks.md` tested oMLX speculative decoding via **`vlm_mtp_enabled`** with a
separate 239 MB drafter (`Qwen3.8-27B-MTP-4bit`) and measured 1.43× on code.

oMLX has a **second, different** path for Qwen3.8: **`mtp_enabled`** — native MTP
(mlx-lm PR 990), which requires a checkpoint with the MTP tensors *fused in*. oMLX logs it
as `Speculative backend selected: Lightning MTP`. That is the path the Reddit post used,
the path the M3 Ultra tuning thread used, and the path we had never tested. It needs
`Jundot/Qwen3.8-27B-oQ4e-mtp` (17 GB, 4-bit g64 with 166 imatrix-selected modules at
5-bit, MTP head fused, vision tower retained).

## 3. Method

Both engines driven by the **same harness code** (`dot/omlx/bench/bench.py`, re-pointed at
each base URL), same three prompt families, same sampler — the official Qwen3.8 contract
**temp 1.0 / top_p 0.95 / top_k 20**, `reasoning_effort: medium` sent both as a top-level
field and via `chat_template_kwargs` (both engines accept both). oMLX's `thinking_budget`
was disabled for the whole comparison because MTPLX has no equivalent; leaving it on would
have capped only oMLX's thinking and shown up as a false wall-clock win.

Per `local-llm-benchmarks.md` confound #2, **one engine resident at a time** and a **fresh
oMLX restart per arm**. Server was idle all day; no foreign traffic.

**Checkpoints are not identical, and cannot be** — each engine requires its own forged
artifact. MTPLX's `Optimized-Speed` is 20.7 GB (4-bit g32 body, 8-bit embeddings/lm_head/
GDN out-projections/last-8 MLP); oMLX's `oQ4e-mtp` is 17 GB. So each arm is measured
**with and without speculation** to separate checkpoint effects from engine effects.

## 4. Results

### Burst decode — 200 tokens, 3 reps, median per family

| Engine | Checkpoint | Speculation | Mean decode | code | Gain |
|---|---|---|---|---|---|
| MTPLX | Optimized-Speed | MTP depth 3 | **47.65** | 54.1 | **2.18×** |
| oMLX | oQ4e-mtp | Lightning MTP | **45.84** | 51.6 | **1.84×** |
| oMLX | mlx-community 4bit | vlm_mtp drafter | 28.66 | 27.9 | 1.42× |
| oMLX | oQ4e-mtp | off | 24.95 | 26.1 | — |
| MTPLX | Optimized-Speed | off (AR) | 21.82 | 22.5 | — |
| oMLX | mlx-community 4bit | off — **what we run today** | 20.14 | 19.8 | — |

MTPLX has the better *multiplier* (2.18× vs 1.84×); oMLX has the better *baseline*
(24.95 vs 21.82, its checkpoint being 17 GB against 20.7 GB, and dense decode is
bandwidth-bound). These very nearly cancel.

MTPLX's 2.18× closely reproduces the 2.29× stamped in its own `mtplx_runtime.json`
(20.4 → 46.8 t/s), so its speed claim is honest and portable.

### Sustained decode — one realistic coding task, generated to 6k–12k tokens

| Arm | Median | Individual runs |
|---|---|---|
| MTPLX + MTP | **34.32** | 36.6 / 32.0 |
| oMLX + Lightning MTP | **22.81** | 31.2 / 17.6 / 27.7 / 17.9 |
| MTPLX AR (no spec) | 16.32 | 16.2 / 16.4 |

**This is the real gap, and it is a defect, not a speed difference.**

oMLX's MTP runs an adaptive depth controller
(`patches/mlx_lm_mtp/batch_generator.py`). After `EXIT_STREAK = 16` consecutive cycles
where speculation fails to beat the taxed baseline by `EXIT_MARGIN`, the sequence is
**handed off to the standard decoder permanently for the rest of that request**
(`_park_mtp_to_standard`). oMLX logs it as `finish=parked`.

Measured over four long generations: **2 of 4 parked**, at 461 and 243 tokens into a 6,000
token answer — so ~95% of those requests ran unaccelerated:

```
MTP[5] finish=length tokens=6000 ... accept 81.4%   -> 31.2 t/s
MTP[6] finish=parked tokens=461  ... accept 79.7%   -> 17.6 t/s
MTP[7] finish=length tokens=6000 ... accept 80.2%   -> 27.7 t/s
MTP[8] finish=parked tokens=243  ... accept 83.1%   -> 17.9 t/s
```

Note the acceptance rate is ~80% in **all four** — the drafter was working fine. The
controller parked anyway. When it does not park, oMLX sustains ~29 t/s, close to MTPLX's
34. MTPLX holds a fixed depth 3 (`--adaptive-policy` defaults to none) and parked in
neither of its runs (n=2 — fewer runs than the oMLX set, so "MTPLX never parks" is not
established, only "not observed").

An earlier hypothesis that this was a prefix-cache-hit fallback was **wrong**: four
repeated short requests all kept MTP engaged at ~36 t/s.

### Prefill — nonce'd + shuffled, `cached_tokens == 0` asserted on every row

| Prompt tokens | MTPLX wall | MTPLX t/s | oMLX (from `local-llm-benchmarks.md`) |
|---|---|---|---|
| ~2K | 12.5 s | 157 | 134 |
| ~8K | 49.7 s | 159 | 150 |
| ~16K | 104.4 s | 152 | 148 |
| ~32K | 225.3 s | 142 | 142 |
| ~64K | 502.8 s | 127 | 126 |

Flat and effectively identical. A 64K context costs ~8.4 minutes to first token on either.
Neither engine's MTP touches prefill — speculation accelerates decode only. oMLX has two
levers MTPLX has no answer to here (`qwen35_ane_prefill_enabled`, `specprefill_enabled`),
untested in this round; the M3 Ultra thread reports ANE prefill as its single biggest win.

### Losslessness — SHA-256 over `reasoning_content + content`, temperature 0, n=3

| Engine | Control (spec off, twice across a restart) | Spec off vs spec on |
|---|---|---|
| MTPLX | **3/3 identical** | **2/3** — one prompt diverged |
| oMLX (Lightning MTP) | **3/3 identical** | **2/3** — one prompt diverged |

Both engines are deterministic at temperature 0, and both change output on one of three
prompts once speculation is on. MTPLX's card claims "Speculation in MTPLX is exact… what
you sample is what the model would have sampled"; it implements the Leviathan-Chen residual
rule (`mtplx/sampling.py:339`), which is distribution-exact but evidently not bit-exact
here.

**This revises `local-llm-benchmarks.md`.** That doc recorded the same 2/3 result for
`vlm_mtp` and called it "an oMLX 0.5.7 bug". It reproduces on oMLX 0.6.3rc2 via a
*different* code path and on a *different vendor's* engine — so it is characteristic of
these MTP implementations generally, not an oMLX defect. n=3 each; suggestive, not proven.

## 5. Costs of adopting MTPLX

- A **second server** on a second port, outside the launchd/nix management that owns oMLX.
- **20.7 GB** duplicate checkpoint of a model we already have twice.
- **One model per process** — no engine pool, so no sharing a box with gemma/roger/frigate.
- Loses oMLX's per-model `model_settings.json`, prefix cache, ANE prefill, specprefill,
  admin API, and the pi/roger/frigate integrations that all point at port 8000.
- MTPLX is a young, single-vendor project whose CLI surface is enormous and whose defaults
  (fan control, "profiles", telemetry-ish receipts) are opaque.

Against that: it is the faster engine for one model on long generations, today, by ~1.5×.

## 6. Recommendation

**Do this:** switch the Qwen3.8-27B specialist from `Qwen3.8-27B-4bit` (no speculation) to
**`Qwen3.8-27B-oQ4e-mtp` with `mtp_enabled: true`**. Measured **20.1 → 45.8 t/s burst,
→ 22.8 t/s sustained**, on the server we already run, with no new daemon, no new port, and
vision retained. Even in the pessimistic parked case it is never slower than what we run now.

**Do not adopt MTPLX.** It wins the sustained number by 1.5×, but that margin exists only
because of an oMLX bug that is likely to be fixed, and buying it costs a parallel serving
stack for exactly one model.

**Caveats to carry:**

- Speculation is **not** bit-lossless on either engine. Our standing policy has been to
  leave it off for that reason. That policy now has to be re-decided rather than inherited:
  the "it's an oMLX bug, wait for a fix" escape hatch is gone. Turning it on is a
  deliberate ~2× speed for non-identical-output trade. My read: **take it for this model** —
  it is a sampling-level difference at temp 1.0, where our own config is already
  non-deterministic by choice, and this model is the "reach for it when A3B failed"
  specialist, not the default.
- **None of this changes the default model.** `Qwen3.6-35B-A3B-4bit` measured 130.7 t/s.
  The best dense-27B number here is 45.8 burst / 22.8 sustained. The MoE remains 3–5×
  faster; this only makes the specialist less painful when you reach for it.
- Worth reporting `finish=parked` upstream — ~80% acceptance with the controller bailing
  anyway looks like a cost-estimator bug, and it is where the remaining 1.5× lives.

## 7. Links

- The post that prompted this — [r/LocalLLaMA: *Benchmark results: what is the best and
  fastest engine to run Qwen3.8-27B on macOS*](https://www.reddit.com/r/LocalLLaMA/comments/1vwbyzr/benchmark_results_what_is_the_best_and_fastest/)
  (u/ex-arman68). A local snapshot is in `~/Downloads/` as of 2026-08-24; read the
  **comments**, which is where the author retracts the oMLX rows.
- The tuning thread that pointed at `mtp_enabled` + ANE prefill —
  [M3 Ultra, 45+ t/s at 8-bit](https://www.reddit.com/r/LocalLLaMA/comments/1vty1g4/been_tweaking_my_qwen_38_setup_up_to_45_steady/)
- **MTPLX** — [mtplx.com](https://mtplx.com) · [github.com/youssofal/mtplx](https://github.com/youssofal/mtplx)
  · [PyPI](https://pypi.org/project/mtplx/) (2.9.1 tested)
- **oMLX** — [github.com/jundot/omlx](https://github.com/jundot/omlx) (0.6.3rc2 tested)
- Checkpoints — [Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed](https://huggingface.co/Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed)
  (4-bit, 20.7 GB; the card is where oMLX's 63.3 t/s is conceded) ·
  [Jundot/Qwen3.8-27B-oQ4e-mtp](https://huggingface.co/Jundot/Qwen3.8-27B-oQ4e-mtp)
  (4-bit fused MTP, 17 GB — **the one we want**) ·
  [Optimized-Quality](https://huggingface.co/Youssofal/Qwen3.8-27B-MTPLX-Optimized-Quality) (8-bit)
- [Speculative decoding (Leviathan et al., ICML 2023)](https://arxiv.org/abs/2211.17192) —
  the probability-ratio + residual-resampling rule both engines implement

## 8. Reproduction

Harness is checked in at **`dot/omlx/bench/engines/`** — engine-agnostic ports of
`dot/omlx/bench/` that take the endpoint as a flag, so both engines run identical
measurement code. Its README has the full matrix and the three traps. Smoke-tested
against the live server after being written, so it works as committed.

```bash
cd ~/Git/toolbox/dot/omlx/bench/engines
cp ../../.omlx/model_settings.json /tmp/ms.bak    # omlx_arm.sh writes the REAL config

pip install mtplx                                  # 2.9.1
mtplx quickstart --model Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed \
    --port 18080 --api-key benchkey --max-tokens 100000   # --no-mtp for the AR arm

./omlx_arm.sh Qwen3.8-27B-oQ4e-mtp native          # Lightning MTP
./sustained.py --arm omlx_mtp --model Qwen3.8-27B-oQ4e-mtp --reps 4 --out sus.json
grep 'MTP\[' ~/Library/Logs/omlx.log               # finish=length good, finish=parked = bailed

cp /tmp/ms.bak ../../.omlx/model_settings.json     # restore, then verify:
git -C ~/Git/toolbox diff --exit-code dot/omlx/.omlx/model_settings.json
```

**Disk:** `~/mtplx-models/` 19 GB (+ symlink in `~/.mtplx/models/`) — safe to delete if
MTPLX is not adopted. `dot/omlx/.omlx/models/Qwen3.8-27B-oQ4e-mtp` 16 GB — keep.

**Standing caveat from `local-llm-benchmarks.md`:** this is a live desktop, absolute numbers
carry ~±20%, and only ratios measured within one pass are trustworthy. Our production
`Qwen3.8-27B-4bit` read 20.14 t/s today against 22.96 in the earlier doc — which is why it
was re-measured in-session rather than compared across sessions.
