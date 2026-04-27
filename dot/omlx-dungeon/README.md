# oMLX Settings for Dungeon (M3 Pro 36GB)

## Hardware Profile
- **Machine**: MacBook Pro 16" M3 Pro
- **RAM**: 36GB unified memory
- **Primary Use**: Client accessing moria's oMLX server; local development tools
- **Architecture**: aarch64-darwin

## Configuration Rationale

### hot_cache_max_size: 8GB

**What it does:**
- Stores KV cache (key-value tensors) from recently processed sequences in RAM
- Caches system prompts so repeated requests don't re-process from scratch
- ~1.55x faster time-to-first-token (TTFT) on cache hits

**Why 8GB for dungeon:**
- M3 Pro has 36GB total unified memory
- 8GB allocated for prefix caching = ~22% of RAM
- Leaves 28GB for:
  - Smaller model weights (7B-13B models: 6-12GB each)
  - Model inference (activation cache, buffers: 5-10GB)
  - OS/system overhead: 3GB

**Constraints vs moria:**
- Dungeon is a MacBook Pro (typically closed/headless, used as server)
- Smaller than moria, so more conservative cache allocation
- Can still run 7B-13B models efficiently with 8GB prefix cache

### Dungeon as Client vs Server

**Note:** Dungeon typically connects to moria's oMLX server remotely:
- qwen-code points to `moria.local:8000` or Tailscale IP
- Dungeon doesn't run its own inference, mostly uses moria's
- This 8GB hot_cache still useful if dungeon runs local tools/agents

**To connect to moria from dungeon:**
```bash
# In qwen-code settings (after stow):
# baseUrl: "http://moria.local:8000/v1"  or
# baseUrl: "http://moria.tail1b9d9.ts.net/v1"  (Tailscale)
```

Dungeon's oMLX config is maintained for future flexibility (running local inference, fallback if moria is down, etc.).

### ssd_cache_dir: null

**What it does:**
- Would spill KV cache to SSD when RAM fills up
- Adds latency

**Why disabled:**
- Single-user, non-concurrent workload
- 8GB cache sufficient for typical usage
- Keep it simple: RAM-only

### Other Settings (Inherited from Base)

- `max_context_window`: 32768 tokens
- `max_model_memory`: "auto"
- `prefill_memory_guard`: true
- `max_concurrent_requests`: 8

## When Dungeon Runs Local Inference

If dungeon needs to run local models (moria offline, testing, etc.):

**Good candidates for 36GB:**
- Qwen3-0.6B: ~1GB, extremely fast
- Llama 3.2 1B: ~1.5GB, very fast
- Qwen2.5 1.5B: ~2GB
- Llama 3.2 3B 4bit: ~2GB
- Qwen3-Coder-7B: ~5GB
- Mistral 7B 4bit: ~5GB

**Models that fit but fill most RAM:**
- Llama 3.2 13B: ~8GB (leaves just 20GB for OS/cache/overhead — tight)
- Qwen3-Coder-14B: ~10GB (too tight)

**Keep dungeon as client, delegate to moria for:**
- 30B+ models
- High concurrency
- Long-context workloads

## Deployment

This config is deployed automatically via NixOS:

```bash
# In hosts/macs/dungeon/default.nix:
system.activationScripts.postActivation.text = lib.mkBefore ''
  cd ~/Git/toolbox/dot
  stow omlx omlx-dungeon
'';
```

After `darwin-rebuild switch`, this settings.json overrides the base config.

## Monitoring

If running local inference on dungeon:
```bash
# Tail logs
tail -f ~/.omlx/logs/*.log | grep -i cache

# Check cache stats
curl -s http://localhost:8000/api/stats | jq .cache
```

## Performance Optimization Tips (from Community)

### Memory Allocation Formula
Model weights should stay under 60% of total unified memory:
- **Formula**: Model RAM (GB) = (Parameters × Bits_per_weight) ÷ 8
- **Example**: Qwen3-Coder-7B 4-bit = (7B × 4) ÷ 8 = 3.5GB
- **Leaves for cache/OS on 36GB**: 36GB - 3.5GB = ~32.5GB (plenty for 8GB prefix cache + OS)

### Quantization Sweet Spot
Q4_K_M quantization:
- **Quality loss**: 3.3% (imperceptible)
- **Size reduction**: 75% (huge!)
- **Use case**: If model doesn't fit, quantize to Q4 instead of reducing hot_cache_max_size

### Context Window & TTFT
- MLX does full prefill before emitting tokens
- At 30K context, TTFT rises linearly with input length
- **Optimization**: Use prefix caching (what we're doing!) to skip re-prefilling large system prompts
- Example: 150ms first run (full prefill), 30ms subsequent runs (cached)

### System-Level Optimizations
1. **Close browsers/Electron apps** — they consume several GB of unified memory
2. **Disable low-power mode** — maintains consistent GPU clock speeds
3. **Use Metal optimization** — MLX uses Apple's Metal for GPU acceleration (automatic)

### Model Selection for 36GB M3 Pro
**Fast options (fits comfortably):**
- Qwen3-0.6B: ~1GB ✅
- Llama 3.2 1B: ~1.5GB ✅
- Qwen2.5 1.5B: ~2GB ✅
- Qwen3-Coder-7B 4bit: ~3.5GB ✅

**Tight fit:**
- Llama 3.2 13B: ~8GB (only 28GB left for cache/OS — risky)

**Better on moria:**
- 30B+ models

### Performance Expectations (Apple Silicon)
- MLX is 20-87% faster than llama.cpp for <14B models
- Single-user with prefix caching: ~1.5x speedup on repeated prompts

## Adjustments

- **Running larger models and getting OOM**: Reduce `hot_cache_max_size` to 4GB, prioritize model weights
- **TTFT slow on first run**: Normal (full prefill). Subsequent runs cached and fast
- **Need more cache, tight on memory**: Use moria as server instead of local inference
- **Close browsers before using**: Frees several GB of unified memory
- **Using dungeon for development, want fastest TTFT**: 8GB cache is well-balanced for this hardware
