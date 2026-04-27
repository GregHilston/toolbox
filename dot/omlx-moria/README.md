# oMLX Settings for Moria (M4 Max 128GB)

## Hardware Profile
- **Machine**: MacBook Pro 14" M4 Max
- **RAM**: 128GB unified memory
- **Primary Use**: LLM hosting for local tools (roger, pi-mono, qwen-code)
- **Architecture**: aarch64-darwin

## Configuration Rationale

### hot_cache_max_size: 32GB

**What it does:**
- Stores KV cache (key-value tensors) from recently processed sequences in RAM
- When roger runs indexing tasks, the system prompt gets cached after first ingestion
- Subsequent requests that share the same system prompt skip expensive re-processing
- ~1.55x faster time-to-first-token (TTFT) on cache hits

**Why 32GB for moria:**
- M4 Max has 128GB total unified memory
- 32GB allocated for prefix caching = ~25% of RAM
- Leaves 96GB for:
  - Large model weights (30B, 120B models: 24-48GB each)
  - Model inference (activation cache, temporary buffers: 10-20GB)
  - OS/system overhead: 5GB
  - Multiple concurrent sequences if needed

**Real-world impact:**
- First run of roger with Qwen3.6-27B 8bit: ~200ms TTFT, full system prompt processing
- Subsequent runs in same session: ~40ms TTFT (5x faster), system prompt cached
- Tool integrations (qwen-code, pi-mono) with large static prompts benefit significantly

### ssd_cache_dir: null

**What it does:**
- Would spill KV cache to SSD when RAM fills up
- Useful for high-concurrency or very large context windows
- Adds latency (SSD is slower than RAM)

**Why disabled:**
- Single-user, non-concurrent workload
- Prefix caching in RAM sufficient
- SSD spilling adds complexity without benefit
- Keep it simple: RAM-only

### Other Settings (Inherited from Base)

- `max_context_window`: 32768 tokens — sufficient for code documents, large prompts
- `max_model_memory`: "auto" — oMLX auto-manages model loading
- `prefill_memory_guard`: true — safety guard prevents OOM during batch processing
- `max_concurrent_requests`: 8 — not used in single-user mode, but harmless

## Testing Cache Effectiveness

**To see prefix caching in action:**

1. **Run roger indexing task** (processes system prompt once):
   ```bash
   cd ~/Git/notes
   # First run (no cache): ~200ms TTFT
   uv run roger index
   ```

2. **Run qwen-code** multiple times in quick succession:
   ```bash
   # All subsequent runs: ~40ms TTFT (system prompt cached)
   qwen-code "explain this function"
   qwen-code "fix this bug"
   ```

3. **Monitor cache stats** (if oMLX UI is running):
   - Check web UI at `localhost:8000` for cache hit rate
   - Should see >70% hit rate after 2-3 requests with same prompt

## Deployment

This config is deployed automatically via NixOS:

```bash
# In hosts/macs/moria/default.nix:
system.activationScripts.postActivation.text = lib.mkBefore ''
  cd ~/Git/toolbox/dot
  stow omlx omlx-moria
'';
```

After `darwin-rebuild switch`, this settings.json overrides the base config.

## Monitoring

Watch oMLX cache effectiveness:
```bash
# Tail logs
tail -f ~/.omlx/logs/*.log | grep -i cache

# Check cache stats (if available in API)
curl -s http://localhost:8000/api/stats | jq .cache
```

## Performance Optimization Tips (from Community)

### Memory Allocation Formula
Model weights should stay under 60% of total unified memory:
- **Formula**: Model RAM (GB) = (Parameters × Bits_per_weight) ÷ 8
- **Example**: Qwen3.6-27B 8-bit = (27B × 8) ÷ 8 = 27GB
- **Leaves for cache/OS**: 128GB - 27GB = ~101GB (plenty of headroom for 32GB prefix cache + other models)

### Quantization Sweet Spot
Q4_K_M quantization:
- **Quality loss**: 3.3% (imperceptible)
- **Size reduction**: 75% (huge!)
- **Use case**: When model is too large, quantize to Q4 instead of reducing hot_cache_max_size

### Context Window & TTFT
- MLX does full prefill before emitting tokens
- At 30K+ context, TTFT rises linearly with input length
- **Optimization**: Use prefix caching (what we're doing!) to skip re-prefilling large system prompts
- Example: 200ms first run (full prefill), 40ms subsequent runs (cached)

### System-Level Optimizations
1. **Close browsers/Electron apps** — they consume several GB, reduce available unified memory
2. **Disable low-power mode** — maintains consistent GPU clock speeds
3. **Use Metal optimization** — MLX uses Apple's Metal for GPU acceleration (automatic)

### Performance Expectations (Apple Silicon)
- MLX is 20-87% faster than llama.cpp for <14B models
- Batching multiple requests: ~4x throughput multiplier
- Single-user with prefix caching: ~1.5x speedup on repeated prompts

## Adjustments

If you notice:
- **Cache misses increasing**: Models don't fit. Use formula above, consider Q4_K_M quantization
- **TTFT slow on first run**: Normal (full prefill). Subsequent runs should be much faster via cache
- **Memory pressure**: Close browsers, reduce hot_cache_max_size to 16GB
- **Need even better prefill speed**: Reduce context_window from 32K to 16K or 8K
