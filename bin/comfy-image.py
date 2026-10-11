#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Generate an image from a prompt with FLUX.2 klein on ComfyUI, and save it.

ComfyUI runs on moria and is reached through Caddy, so this works from any
tailnet host and from inside Hermes. The prompt is used as given: writing a
good one is the calling agent's job (skills/image-generate). Output ends with
a MEDIA: line, the form Hermes attaches; inside Hermes the file goes to its
image cache, the only place its media check accepts.

Usage:
    comfy-image.py "a watercolor of buffalo playing basketball"
    comfy-image.py --seed 7 --width 1344 --height 768 "..."
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import urllib.request
import uuid
from pathlib import Path
from typing import NoReturn
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

SERVER = os.environ.get("COMFY_URL", "https://comfy.grehg2.xyz").rstrip("/")
HERMES_CACHE = Path("/opt/data/cache/images")
TIMEOUT = int(os.environ.get("COMFY_TIMEOUT", "300"))  # a cold load plus a queue


def workflow(prompt: str, seed: int, width: int, height: int, steps: int) -> dict:
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux-2-klein-4b.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "flux2", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae.safetensors"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "5": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["4", 0]}},
        "6": {"class_type": "CFGGuider", "inputs": {"model": ["1", 0], "positive": ["4", 0], "negative": ["5", 0], "cfg": 1}},
        "7": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "8": {"class_type": "Flux2Scheduler", "inputs": {"steps": steps, "width": width, "height": height}},
        "9": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "10": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "11": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["9", 0], "guider": ["6", 0], "sampler": ["7", 0], "sigmas": ["8", 0], "latent_image": ["10", 0]}},
        "12": {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["3", 0]}},
        "13": {"class_type": "SaveImage", "inputs": {"images": ["12", 0], "filename_prefix": "agent"}},
    }


def call(path: str, body: dict | None = None) -> bytes:
    """One request, with every failure turned into a plain error line."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(SERVER + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()
    except HTTPError as e:
        if e.code in (502, 503, 504):
            fail(f"ComfyUI at {SERVER} is down ({e.code}); it runs on moria, which is probably asleep. Wake moria and retry.")
        fail(f"ComfyUI refused {path.split('?')[0]} ({e.code}): {e.read().decode(errors='replace')[:500]}")
    except (URLError, OSError) as e:
        fail(f"cannot reach ComfyUI at {SERVER}: {e}. It runs on moria; check moria is awake and on the tailnet.")


def call_json(path: str, body: dict | None = None) -> dict:
    raw = call(path, body)
    try:
        return json.loads(raw)
    except ValueError:
        fail(f"ComfyUI at {SERVER} returned something other than JSON: {raw[:200].decode(errors='replace')}")


def default_dir() -> Path:
    if os.environ.get("COMFY_IMAGE_DIR"):
        return Path(os.environ["COMFY_IMAGE_DIR"])
    if HERMES_CACHE.is_dir() and os.access(HERMES_CACHE, os.W_OK):
        return HERMES_CACHE
    return Path.home() / "Pictures" / "comfy"


def fail(msg: str) -> NoReturn:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def generate(prompt: str, seed: int, width: int, height: int, steps: int) -> bytes:
    pid = call_json("/api/prompt", {"prompt": workflow(prompt, seed, width, height, steps), "client_id": "comfy-image"})["prompt_id"]
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        hist = call_json(f"/api/history/{pid}")
        if pid in hist:
            entry = hist[pid]
            status = entry.get("status", {})
            if status.get("status_str") != "success":
                errs = [m[1].get("exception_message", "") for m in status.get("messages", []) if m[0] == "execution_error"]
                fail(f"generation failed: {' '.join(errs).strip() or status}")
            img = next((i for o in entry.get("outputs", {}).values() for i in o.get("images", [])), None)
            if img is None:
                fail("ComfyUI finished but returned no image; run again with a new seed.")
            q = urlencode({"filename": img["filename"], "subfolder": img["subfolder"], "type": img["type"]})
            return call(f"/api/view?{q}")
        time.sleep(0.5)
    fail(f"no image after {TIMEOUT}s; ComfyUI may be busy. Its queue is at {SERVER}.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("prompt")
    ap.add_argument("--seed", type=int, help="reuse one to change the prompt but keep the composition")
    ap.add_argument("--width", type=int, default=1024)
    ap.add_argument("--height", type=int, default=1024)
    ap.add_argument("--steps", type=int, default=4)
    ap.add_argument("--out", type=Path, help="directory to save into")
    a = ap.parse_args()
    if not a.prompt.strip():
        fail("the prompt is empty")
    if a.width % 16 or a.height % 16 or not (256 <= a.width <= 2048 and 256 <= a.height <= 2048):
        fail("width and height must be multiples of 16 between 256 and 2048")
    seed = a.seed if a.seed is not None else random.randint(1, 2**31 - 1)

    start = time.time()
    png = generate(a.prompt, seed, a.width, a.height, a.steps)
    out_dir = a.out or default_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"comfy-{uuid.uuid4().hex[:12]}.png"
    path.write_bytes(png)
    print(f"prompt: {a.prompt}")
    print(f"seed: {seed}  size: {a.width}x{a.height}  steps: {a.steps}  seconds: {time.time() - start:.0f}")
    print(f"MEDIA:{path}")


if __name__ == "__main__":
    main()
