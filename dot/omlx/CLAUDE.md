# oMLX

Dotfiles for oMLX LLM inference server, stowed to `~/.omlx`. Host-specific overlays (`omlx-moria`, `omlx-dungeon`) are stowed on top during nix-darwin activation.

## Restarting

oMLX runs as a launchd user agent (`org.nixos.omlx`):

```bash
launchctl kickstart -k gui/$(id -u)/org.nixos.omlx
```

## Per-Model Settings

oMLX supports per-model overrides for sampling, thinking, KV cache, and more via `model_settings.json` (lives alongside `settings.json` in `~/.omlx/`). These override the global `sampling.*` defaults in `settings.json` for a specific model only.

The file is created automatically the first time you change a model's settings through the admin panel, but we manage it in stow so it deploys declaratively. Schema:

```json
{
  "version": 1,
  "models": {
    "Model-ID-Here": {
      "temperature": 0.6,
      "top_p": 0.95,
      "top_k": 20
    }
  }
}
```

Available per-model fields (not exhaustive): `temperature`, `top_p`, `top_k`, `min_p`, `repetition_penalty`, `presence_penalty`, `max_tokens`, `max_context_window`, `enable_thinking`, `preserve_thinking`, `thinking_budget_tokens`, `turboquant_kv_enabled`, `turboquant_kv_bits`, `is_pinned`, `is_default`, `ttl_seconds`, `model_alias`, `model_type_override`, `chat_template_kwargs`, `force_sampling`.

There are also `model_profiles.json` (named presets per model) and `global_templates.json` (reusable templates across models), but we don't use those yet.

## Gotcha: Global Context Window Cap

`settings.json` has a `sampling.max_context_window` that caps **all** models server-wide. If a tool (pi, qwen-code, etc.) reports "exceeds max context window" with a surprisingly low limit, check this value — it overrides per-model context windows configured in the tool's own settings.
