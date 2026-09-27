---
name: home-assistant
description: Read live Home Assistant state — is a door locked, is anything open, what is the thermostat doing, which battery is low. Use whenever the user asks about the house, a device, or a sensor. Read-only; it cannot control anything.
---

# Home Assistant (read-only)

One script, on `$PATH` from toolbox `bin/`:

```bash
ha-state.py                     # every entity: id, state, friendly name (200 lines max)
ha-state.py lock                # one domain: lock, binary_sensor, climate, sensor, cover, light…
ha-state.py lock.frontdoor_lock # one entity with its attributes
```

Go from broad to narrow: a domain first, then the one entity you need. The full list is
long; never dump it into the conversation. Useful roll-ups already exist as
`binary_sensor.any_door_unlocked`, `binary_sensor.any_low_battery` and
`binary_sensor.any_water_leak`.

**Read-only by construction.** The script only ever GETs, and its token belongs to an HA
user in the `system-read-only` group, so a request to lock, unlock, switch or set anything
cannot be honoured. Say so; do not look for another way.

## Setup

`~/.pi/agent/homeassistant.json` is rendered by `just secrets` in `toolbox/nixos` from
`homeassistant.json.tpl` (token `Infra/Hermes/hass_token_pi_harness`, one token per
consumer so it can be revoked alone). The endpoint is `https://home-assistant.grehg2.xyz`,
so the machine must be on the tailnet. `HA_URL` / `HA_BEARER` override the file.

## Tool mapping

| Generic move | Claude Code | pi |
| --- | --- | --- |
| Run the script | `Bash` | `bash` |
