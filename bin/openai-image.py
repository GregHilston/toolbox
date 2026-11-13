#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Generate images with OpenAI's Images API (gpt-image-2) at a fixed quality, and save them.

The paid API honours quality and size, so every image comes out the same way; the free
ChatGPT Plus route picks low or medium at random and ignores both (measured 2026-11-12,
loser-picks docs/art/image-models.md). The key comes from OPENAI_API_KEY or 1Password
("chatgpt loser picks art api key" in Infra) and is never printed.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import NoReturn

URL = "https://api.openai.com/v1/images/generations"
OP_REF = "op://Infra/big5y2jhb5cwfkvxfpmbpeiit4/credential"  # "chatgpt loser picks art api key"
SIZES = ("1024x1024", "1536x1024", "1024x1536")


def fail(msg: str) -> NoReturn:
    print(f"openai-image: {msg}", file=sys.stderr)
    sys.exit(1)


def api_key() -> str:
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"]
    token = Path.home() / ".config/op/service-account-token"
    if not token.is_file():
        fail(f"no OPENAI_API_KEY and no 1Password token at {token}")
    env = {**os.environ, "OP_SERVICE_ACCOUNT_TOKEN": token.read_text().strip()}
    r = subprocess.run(["op", "read", OP_REF], capture_output=True, text=True, env=env, timeout=30)
    if r.returncode != 0 or not r.stdout.strip():
        fail(f"could not read {OP_REF} from 1Password: {r.stderr.strip()[:200]}")
    return r.stdout.strip()


def multipart(fields: dict, files: list[Path]) -> tuple[bytes, str]:
    boundary = "openaiimage" + str(time.time_ns())
    out = b""
    for k, v in fields.items():
        out += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    for f in files:
        out += f'--{boundary}\r\nContent-Disposition: form-data; name="image[]"; filename="{f.name}"\r\nContent-Type: image/png\r\n\r\n'.encode()
        out += f.read_bytes() + b"\r\n"
    return out + f"--{boundary}--\r\n".encode(), f"multipart/form-data; boundary={boundary}"


def generate(prompt: str, quality: str, size: str, n: int, refs: list[Path]) -> list[bytes]:
    fields = {"model": "gpt-image-2", "prompt": prompt, "quality": quality, "size": size, "n": n}
    if refs:
        body, ctype = multipart(fields, refs)
        url = URL.replace("generations", "edits")
    else:
        body, ctype, url = json.dumps(fields).encode(), "application/json", URL
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": "Bearer " + api_key(),
        "Content-Type": ctype,
    })
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read()[:400].decode(errors="replace")
        if e.code == 401:
            fail("OpenAI refused the key (401); check the 1Password item")
        if e.code == 429:
            fail(f"rate limit or spend cap reached (429): {detail}")
        fail(f"HTTP {e.code}: {detail}")
    except urllib.error.URLError as e:
        fail(f"could not reach api.openai.com: {e.reason}")
    usage = data.get("usage") or {}
    print(f"quality {quality}, size {size}, tokens in {usage.get('input_tokens', '?')} out {usage.get('output_tokens', '?')}", file=sys.stderr)
    log_spend(usage, quality, size, len(data["data"]))
    return [base64.b64decode(d["b64_json"]) for d in data["data"]]


# USD per 1M tokens: text in, image in, image out (pricing page, 2026-11-13).
PRICE = (5.00, 8.00, 30.00)
LEDGER = Path(os.environ.get("OPENAI_IMAGE_LEDGER", Path.home() / ".cache" / "openai-image" / "ledger.jsonl"))


def log_spend(usage: dict, quality: str, size: str, n: int) -> None:
    """Append one line per call, which usage-mark.py sums."""
    d = usage.get("input_tokens_details") or {}
    text_in = d.get("text_tokens", usage.get("input_tokens", 0) or 0)
    image_in = d.get("image_tokens", 0) or 0
    out = usage.get("output_tokens", 0) or 0
    cost = (text_in * PRICE[0] + image_in * PRICE[1] + out * PRICE[2]) / 1e6
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as fh:
        fh.write(json.dumps({"t": time.time(), "model": "gpt-image-2", "quality": quality, "size": size, "n": n,
                             "text_in": text_in, "image_in": image_in, "out": out, "usd": round(cost, 5)}) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("prompt")
    ap.add_argument("--quality", choices=("low", "medium", "high"), default="medium")
    ap.add_argument("--size", choices=SIZES, default="1536x1024")
    ap.add_argument("--ref", type=Path, action="append", default=[], help="reference image to match the style of (repeatable); uses the edits endpoint")
    ap.add_argument("--n", type=int, default=1, help="variants from one call, saved as NAME-1.png, NAME-2.png, ...")
    ap.add_argument("--out", type=Path, help="directory to save into (default ~/Pictures/openai)")
    ap.add_argument("--name", help="file name without .png (default from the prompt and time)")
    a = ap.parse_args()
    out_dir = a.out or Path(os.environ.get("OPENAI_IMAGE_DIR", Path.home() / "Pictures" / "openai"))
    out_dir.mkdir(parents=True, exist_ok=True)
    name = a.name or (re.sub(r"[^a-z0-9]+", "-", a.prompt.lower())[-40:].strip("-") + time.strftime("-%H%M%S"))
    images = generate(a.prompt, a.quality, a.size, a.n, a.ref)
    for i, img in enumerate(images, 1):
        path = out_dir / (f"{name}.png" if len(images) == 1 else f"{name}-{i}.png")
        path.write_bytes(img)
        print(f"MEDIA:{path}")


if __name__ == "__main__":
    main()
