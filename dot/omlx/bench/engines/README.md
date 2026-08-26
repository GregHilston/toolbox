# Cross-engine harness

The scripts behind **`docs/mtplx-vs-omlx.md`** (MTPLX vs oMLX for Qwen3.8-27B).

The scripts one directory up are oMLX-only — they hardcode `127.0.0.1:8000`. These take
the endpoint as a flag so **oMLX and MTPLX are measured by identical code**, which is the
only way an engine comparison means anything. They import `bench.py` rather than copying
its `stream_once()`, so these numbers stay commensurable with `local-llm-benchmarks.md`.

| script | measures |
|---|---|
| `burst.py` | decode t/s + TTFT, 200 tokens, 3 reps over code/prose/qa |
| `sustained.py` | decode t/s over a 6k–12k-token answer — **the arm that found the real difference** |
| `prefill.py` | prefill cost vs prompt length (~2K–64K), nonce'd + shuffled |
| `lossless.py` | whether speculation changes output (with the mandatory off-vs-off control) |
| `omlx_arm.sh` | patch `model_settings.json` + restart oMLX clean, one arm at a time |

Key comes from `$OMLX_API_KEY` or the gitignored `../omlx_key`; pass `--key` for a
non-oMLX engine.

## Three things that will bite you

1. **Burst decode is not the answer.** 200 tokens said the two engines were within 4%.
   Sustained generation said one was 1.5× faster. Always run `sustained.py`, `--reps 4`
   minimum — the effect it catches is intermittent (2 of 4 runs).
2. **One engine resident at a time**, and a fresh oMLX restart per arm — confound #2 in
   `local-llm-benchmarks.md`. Stop MTPLX before measuring oMLX and vice versa.
3. **`omlx_arm.sh` writes to the real stowed `model_settings.json`.** Back it up and
   diff it back to clean afterwards; the header comment has the exact commands.

## The matrix that produced the doc

```bash
cd ~/Git/toolbox/dot/omlx/bench/engines
cp ../../.omlx/model_settings.json /tmp/ms.bak          # ALWAYS

# --- MTPLX (oMLX stopped) ---
pip install mtplx                                        # 2.9.1
huggingface-cli download Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed \
  --local-dir ~/.mtplx/models/Youssofal--Qwen3.8-27B-MTPLX-Optimized-Speed
mtplx quickstart --model Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed \
  --port 18080 --api-key benchkey --max-tokens 100000    # add --no-mtp for the AR arm
M="--base http://127.0.0.1:18080/v1 --key benchkey --model mtplx-qwen38-27b-optimized-speed"
./burst.py     --arm mtplx_mtp $M --out arm_mtplx_mtp.json
./sustained.py --arm mtplx_mtp $M --reps 4 --out sus_mtplx_mtp.json

# --- oMLX (MTPLX stopped) ---
./omlx_arm.sh Qwen3.8-27B-oQ4e-mtp native
./burst.py     --arm omlx_mtp --model Qwen3.8-27B-oQ4e-mtp --out arm_omlx_mtp.json
./sustained.py --arm omlx_mtp --model Qwen3.8-27B-oQ4e-mtp --reps 4 --out sus_omlx_mtp.json
grep 'MTP\[' ~/Library/Logs/omlx.log   # finish=length = MTP held; finish=parked = it bailed

cp /tmp/ms.bak ../../.omlx/model_settings.json          # restore, then verify:
git -C ~/Git/toolbox diff --exit-code dot/omlx/.omlx/model_settings.json
```

`finish=parked` is the single most important string in this directory — it is oMLX's MTP
depth controller permanently handing a request back to the standard decoder, and it is
where the entire measured difference between the two engines came from.
