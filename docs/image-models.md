# Local image generation on moria

Why ComfyUI runs FLUX.2 klein 4B on moria, and the numbers a new model or runtime must
beat. Measured 2026-10-11. Running and upgrading it: `nixos/CLAUDE.md` → "ComfyUI on
moria".

## moria throttles, and that decides everything

moria is a **14-inch** MacBook Pro M4 Max (Mac16,6). An MLX bf16 matmul measured 13.4
TFLOPS from idle, then held about 3.6 TFLOPS after two minutes of load, in the default
power mode. Memory, swap, oMLX traffic and prompt length were all ruled out.

So a model is only usable here if one image finishes inside that first burst. Few-step
distilled models do; 20 to 50 step models do not.

## Measured (1024², same three prompts, seed 42)

| Model | Runtime | Single image | Six back to back | Verdict |
|---|---|---|---|---|
| **FLUX.2 klein 4B**, 4 steps | ComfyUI (MPS) | 16 s | 14 → 19 s | **chosen**: fast, strong photos and scenes, Apache-2.0 |
| FLUX.2 klein 4B | mflux (MLX) | 13 s | 14 → 15 s | as fast, but a CLI with no server or UI |
| FLUX.2 klein 4B | Draw Things gRPC | 16 s | 14 → 16 s | fastest per step (2.3 s); ComfyUI node only, no ecosystem |
| Z-Image-Turbo (4-bit), 9 steps | mflux | 50 s | 53 → 74 s | better text, weaker scenes, 4× slower |
| Qwen-Image-2.1, 25 steps | ComfyUI (MPS) | 8.5 min | 12 → 15 min | perfect text; infeasible once throttled |

klein's weakness is text inside images ("EXPREESS"). Z-Image-Turbo got one typo, Qwen
none.

## Hosting options considered

- **ComfyUI on moria, Caddy on dungeon** — chosen. One app, the full custom-node and
  LoRA ecosystem, and `comfy.grehg2.xyz` shows a "moria is asleep" page when it is.
- **ComfyUI on dungeon handing jobs to Draw Things on moria** — works (15 s) and the
  UI stays up, but generation goes through Draw Things' own sampler node, so ComfyUI's
  ecosystem does not apply. The server needs `--no-tls`: its certificate fails for an IP.
- **ComfyUI-Distributed, dungeon master and moria worker** — works (16 s) with LoRAs,
  but two ComfyUIs kept in lockstep, special nodes in every workflow, and a master that
  falls back to rendering locally when the worker is away.

## Re-evaluating

A candidate has to finish one 1024² image in well under a minute from idle and survive
six in a row without falling off a cliff. Run it from idle (wait a few minutes after
the last GPU job), then back to back, and look at the images, not just the times.
High Power Mode (`sudo pmset -a powermode 2`) would raise the throttled ceiling; it was
not tested.
