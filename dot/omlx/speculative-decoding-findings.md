# Speculative decoding on oMLX / Apple Silicon — findings

**TL;DR — do not add an MTP/assistant drafter or other speculative decoding to our
Gemma 4 (or similar low-active-param MoE) on Apple Silicon. We measured it on two
machines and it was a net *loss* on both (moria 0.97×, dungeon 0.91×). The technique
that wins big on a bandwidth-starved discrete GPU does not transfer to MLX here. This
doc exists so we don't re-try it without new reason.**

Date: 2026-06-12. oMLX 0.4.4rc1. Tested by: Greg + Claude.

---

## What prompted this

An r/LocalLLaMA post — ["120 tok/s on 12GB VRAM with Gemma 4 12B QAT MTP"](https://www.reddit.com/r/LocalLLaMA/comments/1typjmc/120_toks_on_12gb_vram_with_gemma_4_12b_qat_mtp/)
(u/janvitos, "Tutorial | Guide") — paired a QAT Gemma 4 12B with Google's tiny
**MTP "assistant" drafter** and went from **60 → 120 tok/s (~2×)** on an RTX 4070 Super
12GB, at 65.8% draft acceptance, lossless. The post used a patched llama.cpp
(`--spec-type draft-mtp --spec-draft-n-max 4`).

Two ideas to evaluate against how we run oMLX (moria/citadel/dungeon):
1. **MTP speculative decoding** — the speed trick.
2. **QAT checkpoints** — better quality at 4-bit.

## How speculative decoding works (and why it's lossless)

A small fast *drafter* proposes several tokens; the large *target* verifies them in one
forward pass and accepts the longest prefix it would itself have produced. Greedy
verification is **lossless by construction** — output is identical to running the target
alone (we confirmed: same prompt is deterministic, hash-identical across runs). The win
comes from doing *one* expensive target pass instead of N sequential ones — but **only if
the target pass is the bottleneck**, i.e. decode is memory-bandwidth-bound.

Reference: Leviathan et al., "Fast Inference from Transformers via Speculative Decoding"
(2023). Google's Gemma 4 MTP drafters:
<https://blog.google/innovation-and-ai/technology/developers-tools/multi-token-prediction-gemma-4/>
("up to 3× speedup without degradation"; lists MLX as a supported backend).

## oMLX support (so a future reader knows the knobs exist)

oMLX 0.4.2+ supports several **mutually exclusive** per-model speculative paths, set in
`~/.omlx/model_settings.json`:
- `vlm_mtp_enabled` + `vlm_mtp_draft_model` + `vlm_mtp_draft_block_size` — external MTP
  "assistant" drafter (Gemma 4 assistant or Qwen MTP). This is the path the Gemma 4
  drafter uses (gemma-4-26B-A4B is a unified/VLM model).
- `mtp_enabled` — the model's **built-in** MTP head. Qwen 3.5/3.6 & Deepseek-v4 only, and
  only if the checkpoint ships `mtp.*` weights. **Our Qwen3.6-35B-A3B-8bit does not** — its
  config declares MTP heads but the quant ships no MTP weights, so oMLX skips attachment.
- `dflash_*` — DFlash block-diffusion drafter (separate external draft model).
- `specprefill_*` — speculative prefill.

The full field list is in the `ModelSettingsRequest` schema:
`<omlx-cellar>/libexec/lib/python3.11/site-packages/omlx/admin/routes.py` (also
`GET http://127.0.0.1:8000/openapi.json`). Drafter for our model:
[`mlx-community/gemma-4-26B-A4B-it-assistant-bf16`](https://huggingface.co/mlx-community/gemma-4-26B-A4B-it-assistant-bf16)
(831 MB; QAT pair is `...-qat-assistant-nvfp4`). The drafter is a per-host download (the
models dir is stow-ignored).

## What we measured

Matched A/B, same server instance, temperature 0, identical prompts. Speed = completion
tokens / wall time. Drafter draft-acceptance was healthy and **identical across hosts**
(it's a model/prompt property, not hardware): code ~78%, prose ~63%, qa ~54%.

### moria — Apple M4 Max, 128 GB

| prompt (500/200 tok) | drafter OFF | drafter ON | speedup |
|---|---|---|---|
| code | 107.6 t/s | 116.3 | **1.08×** |
| prose | 107.0 t/s | 103.4 | 0.97× |
| qa | 103.0 t/s | 92.3 | 0.90× |
| **avg** | — | — | **0.97×** |

### dungeon — Apple M3 Pro, 36 GB

| prompt | drafter OFF | drafter ON | speedup |
|---|---|---|---|
| code | 43.3 t/s | 43.6 | 1.01× |
| prose | 43.5 t/s | 38.7 | 0.89× |
| qa | 42.0 t/s | 35.2 | 0.84× |
| **avg** | — | — | **0.91×** |

Only highly-predictable code generation broke even-to-slightly-positive; everything else
lost. **Net negative on both chips.**

## Why it doesn't work here (the important part)

1. **Low-active-param MoE.** gemma-4-26B-A4B activates only **~4B params per token**. Decode
   reads ~4B × 0.5 byte (4-bit) ≈ 2 GB/token — cheap. There is very little target-model time
   for the drafter to save.
2. **Apple Silicon isn't the bottleneck the trick exploits.** The Reddit 2× came from a 12 GB
   GPU that is *memory-bandwidth-starved* on a dense-ish workload. The M4 Max has ~546 GB/s of
   unified bandwidth; the model is small-active. Decode isn't bandwidth-bound, so speculative
   decoding has nothing to recover.
3. **The drafter has real overhead.** Each round runs the drafter *and* verifies multiple
   target tokens, ~35–45% of which are rejected (acceptance ~55–78%). That wasted compute
   plus the drafter forward passes exceed the savings.
4. **Lower bandwidth did NOT help (hypothesis disproved).** We expected the bandwidth-tighter
   M3 Pro to benefit. It was *worse* (0.91× vs 0.97×) because it is also **compute**-starved —
   the drafter overhead hurts more, not less, on a slower GPU.

### When speculative decoding *would* be worth re-testing

- A **large dense** model (e.g. a 30B+ dense, not a small-active MoE), where each target
  decode step is genuinely expensive / bandwidth-bound.
- A model whose checkpoint ships **native MTP weights** (`mtp_enabled`, single-stream) — near
  zero extra memory, no separate drafter overhead. Our Qwen3.6 quants don't ship them today.
- A much higher draft-acceptance regime (very templated output).

If none of those change, don't bother.

## The QAT half — KEPT (this one is a win)

Separately from speed, we swapped gemma to the **quantization-aware-trained** 4-bit
checkpoint [`mlx-community/gemma-4-26B-A4B-it-qat-4bit`](https://huggingface.co/mlx-community/gemma-4-26B-A4B-it-qat-4bit).
Same ~15 GB footprint and **identical speed** (75.9 vs 76.0 t/s), better quality at 4-bit by
construction (Google simulates quantization during training:
<https://blog.google/innovation-and-ai/technology/developers-tools/quantization-aware-training-gemma-4/>).
It is now the canonical gemma (`gemma-4-26b-a4b-it-qat-4bit`); pi's registry
(`dot/pi/.pi/agent/models.json.tpl`) points at it. The old post-training-quant model was
deleted. **Lesson: prefer the QAT checkpoint whenever one exists — it's free.**

## Reproduction (if ever needed)

```bash
# 1. download the drafter into the models dir (per host; models dir is stow-ignored)
PY=/opt/homebrew/Cellar/omlx/*/libexec/bin/python3
$PY -c "from huggingface_hub import snapshot_download as d; \
  d('mlx-community/gemma-4-26B-A4B-it-assistant-bf16', \
    local_dir='$HOME/Git/toolbox/dot/omlx/.omlx/models/gemma-4-26B-A4B-it-assistant-bf16')"

# 2. in the gemma model_settings entry, add (exclusive with dflash/mtp/specprefill):
#    "vlm_mtp_enabled": true,
#    "vlm_mtp_draft_model": "gemma-4-26B-A4B-it-assistant-bf16",
#    "vlm_mtp_draft_block_size": 4

# 3. restart and watch the drafter load + acceptance stats:
launchctl kickstart -k gui/$(id -u)/org.nixos.omlx
grep -E "VLM MTP|vlm_mtp stats" ~/Library/Logs/omlx.log | tail

# 4. A/B: hit /v1/chat/completions at temp 0 with the same prompts, drafter off vs on,
#    compare completion_tokens / wall_time. (lossless => identical output same-instance.)
```

## Sources

- Reddit demo: <https://www.reddit.com/r/LocalLLaMA/comments/1typjmc/120_toks_on_12gb_vram_with_gemma_4_12b_qat_mtp/>
- llama.cpp Gemma 4 MTP PR: <https://github.com/ggml-org/llama.cpp/pull/23398>
- Google — Gemma 4 MTP drafters: <https://blog.google/innovation-and-ai/technology/developers-tools/multi-token-prediction-gemma-4/>
- Google — Gemma 4 QAT: <https://blog.google/innovation-and-ai/technology/developers-tools/quantization-aware-training-gemma-4/>
- Drafter (bf16 / QAT nvfp4): <https://huggingface.co/mlx-community/gemma-4-26B-A4B-it-assistant-bf16> · <https://huggingface.co/mlx-community/gemma-4-26B-A4B-it-qat-assistant-nvfp4>
- QAT base: <https://huggingface.co/mlx-community/gemma-4-26B-A4B-it-qat-4bit>
- oMLX: <https://github.com/jundot/omlx>
- Speculative decoding (theory): Leviathan, Kalman, Matias — "Fast Inference from Transformers via Speculative Decoding," ICML 2023, <https://arxiv.org/abs/2211.17192>
