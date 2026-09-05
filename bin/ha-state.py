#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Home Assistant state, read-only. GET is the only verb, and the token belongs to an HA
user in the system-read-only group (home-lab/hermes/README.md step 8), so nothing here can
actuate a device.

    ha-state.py                 every entity: id, state, friendly name (200 lines max)
    ha-state.py <domain>        one domain, e.g. lock, binary_sensor, climate
    ha-state.py <entity_id>     one entity with its attributes

Endpoint and token come from HA_URL / HA_BEARER, else ~/.pi/agent/homeassistant.json
(rendered by `just secrets` in toolbox/nixos). The same script, in bash, serves Hermes:
home-lab/hermes/scripts/ha-state.sh.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ENTITY_ID = re.compile(r"^[a-z_][a-z0-9_]*\.[a-z0-9_]+$")
CONFIG = Path.home() / ".pi" / "agent" / "homeassistant.json"


def credentials() -> tuple[str, str]:
    url, token = os.environ.get("HA_URL", ""), os.environ.get("HA_BEARER", "")
    if not (url and token) and CONFIG.is_file():
        cfg = json.loads(CONFIG.read_text())
        url, token = url or cfg.get("url", ""), token or cfg.get("token", "")
    if not (url and token):
        sys.exit(f"ha-state: HA_URL/HA_BEARER unset and {CONFIG} missing; run `just secrets` in toolbox/nixos")
    return url.rstrip("/"), token


def get(path: str):
    url, token = credentials()
    req = urllib.request.Request(url + path, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        sys.exit(f"ha-state: GET {path} -> HTTP {e.code} against {url}")
    except (urllib.error.URLError, TimeoutError) as e:
        sys.exit(f"ha-state: GET {path} failed against {url}: {e}")


def main(argv: list[str]) -> None:
    arg = argv[1] if len(argv) > 1 else ""
    if "." in arg:
        if not ENTITY_ID.match(arg):
            sys.exit(f"ha-state: not an entity id: {arg}")
        e = get(f"/api/states/{arg}")
        print(e["entity_id"], e["state"], "changed " + e.get("last_changed", ""), sep="\t")
        attrs = json.dumps(e.get("attributes", {}), ensure_ascii=False)
        print(attrs[:1500] + (" …" if len(attrs) > 1500 else ""))
        return
    rows = sorted(get("/api/states"), key=lambda e: e["entity_id"])
    if arg:
        rows = [e for e in rows if e["entity_id"].split(".", 1)[0] == arg]
    if not rows:
        print(f"no entities in {arg}" if arg else "no entities")
        return
    for e in rows[:200]:
        print(e["entity_id"], e["state"], e.get("attributes", {}).get("friendly_name", ""), sep="\t")
    if len(rows) > 200:
        print(f"… {len(rows) - 200} more; ask for one domain")


if __name__ == "__main__":
    main(sys.argv)
