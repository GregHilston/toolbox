# Strata: the heavy local model on moria

[Strata](https://github.com/Niko1221/Strata) serves Qwen3.8-Flash-Next (125B mixture of
experts, 6B active) on moria, behind the gateway's `local-big`. It is a llama.cpp/ggml fork
with its own Metal engine, not MLX. Why this model and engine: `docs/model-evaluation.md`
and the 2026-10-26 section of `docs/local-llm-benchmarks.md`.

## Layout

| what | where |
|---|---|
| launchd agent `org.nixos.strata` | `nixos/modules/darwin/strata.nix`, enabled in `hosts/macs/moria` |
| install, upgrade, pinned commit | `bin/strata-setup.sh` (`just strata-setup` from `nixos/`) |
| checkout and engine build | `~/Git/strata`, detached at the pin |
| model files (~86 GB) | `~/Git/Strata-data` |
| config the agent reads | `~/Git/strata/strata.json`, a link to the `strata-<pack>.json` setup writes |
| log | `~/Library/Logs/strata.log` |

It listens on moria's tailnet address, port 8080, and takes oMLX's API key, read from
`~/.omlx/settings.json` at start. Model id: `qwen3.8-flash-next-iq3_s`.

## Behaviour

- **Lazy.** The agent starts with the model unloaded (~220 MB). The first request loads it
  in 20–70 s, depending on page cache; it unloads after 30 minutes idle (`idle_unload_s`). Loaded, it maps a
  54.8 GB file and peaks at 18 GB of its own, beside oMLX's A3B.
- **Defaults** (`bin/strata-setup.sh` adds them after every setup run, which rewrites the
  config): `reasoning_effort: medium`, a 16384-token thinking budget. Strata's own sampling
  defaults for thinking requests are the model card's (temp 1.0, top_p 0.95, top_k 20).
- **64K context**, set by Strata's wizard. A 64K prompt takes ~4.4 min to first token.
- **Text only.** The vision encoder is off (`--vision no`).

## Upgrading

The pin is `REF` in `bin/strata-setup.sh`, a commit, because Strata releases daily and 2.x
broke LAN auth. Never run Strata's own `update.sh`. To move it: change `REF`, run
`just strata-setup` (it rebuilds when the commit changed and restarts the agent), then
re-run the CRUD eval (`dot/omlx/bench/`, ported to 8080 as the 2026-10-26 section says)
before committing the new pin.

The build must use Apple's clang. nix-darwin's `cc` carries the 14.4 SDK and the Metal build
fails with it; the script sets the toolchain.

## Operating it

```sh
launchctl kickstart -k "gui/$(id -u)/org.nixos.strata"   # restart
tail -f ~/Library/Logs/strata.log
curl -s -H "Authorization: Bearer $KEY" http://100.115.155.85:8080/v1/models   # status: loaded or unloaded
```

## Rolling back to Swift-27B on oMLX

Swift's weights are still in oMLX's model folder. Put
`models."Swift-1.5-Qwen3.8-27b-oQ4e-mtp" = "yottle/Swift-1.5-Qwen3.8-27b-oQ4e-mtp";` back in
`services.omlxDeploy` in `hosts/macs/moria`, disable `custom.services.strata`, and point
`local-big` in home-lab `litellm/config.yaml` back at
`openai/Swift-1.5-Qwen3.8-27b-oQ4e-mtp` on port 8000 (and the port in its config test).
