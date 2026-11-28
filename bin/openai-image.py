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
import http.client
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import uuid
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


class HTTPStatus(Exception):
    def __init__(self, code: int, body: bytes):
        self.code, self.body = code, body


def connect(url: str) -> http.client.HTTPConnection:
    """A connection to url, tunnelled through HTTPS_PROXY when one is set."""
    u = urllib.parse.urlsplit(url)
    if u.scheme != "https":
        return http.client.HTTPConnection(u.netloc, timeout=300)
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if not proxy:
        return http.client.HTTPSConnection(u.netloc, timeout=300)
    p = urllib.parse.urlsplit(proxy)
    conn = http.client.HTTPSConnection(p.hostname or "", p.port or 80, timeout=300)
    auth = {}
    if p.username:
        cred = f"{urllib.parse.unquote(p.username)}:{urllib.parse.unquote(p.password or '')}"
        auth = {"Proxy-Authorization": "Basic " + base64.b64encode(cred.encode()).decode()}
    conn.set_tunnel(u.hostname or "", u.port or 443, headers=auth)
    return conn


def generate(prompt: str, quality: str, size: str, n: int, refs: list[Path], fmt: str) -> list[bytes]:
    fields: dict = {"model": "gpt-image-2", "prompt": prompt, "quality": quality, "size": size, "n": n,
                    "output_format": fmt}
    if fmt != "png":
        fields["output_compression"] = COMPRESSION
    if refs:
        body, ctype = multipart(fields, refs)
        url = URL.replace("generations", "edits")
    else:
        body, ctype, url = json.dumps(fields).encode(), "application/json", URL
    headers = {"Authorization": "Bearer " + api_key(), "Content-Type": ctype}
    path = urllib.parse.urlsplit(url).path
    call = {"model": "gpt-image-2", "quality": quality, "size": size, "n": n, "format": fmt}
    for attempt in (1, 2):
        cid = uuid.uuid4().hex[:12]
        estimate = estimate_usd(prompt, quality, size, n)
        log(cid, "sent", estimate, call)
        conn = connect(url)
        try:
            # Not urllib: its Connection: close lets the sandbox proxy drop the tail.
            conn.request("POST", path, body=body, headers=headers)
            r = conn.getresponse()
            raw = r.read()
            if r.status != 200:
                raise HTTPStatus(r.status, raw)
            data = json.loads(raw)
        except (http.client.IncompleteRead, json.JSONDecodeError) as e:
            got = len(e.partial) if isinstance(e, http.client.IncompleteRead) else len(raw)
            log(cid, "truncated", 0.0, {**call, "bytes": got})
            if attempt == 1:
                print(f"openai-image: response cut off after {got} bytes; retrying once", file=sys.stderr)
                continue
            fail(f"response cut off twice (last after {got} bytes); both calls are likely billed. "
                 "A sandbox proxy can do this: try --format jpeg, or run outside the sandbox")
        except HTTPStatus as e:
            detail = e.body[:400].decode(errors="replace")
            refused = e.code == 400 and "safety" in detail
            # A refusal may be billed: keep it.
            log(cid, "refused" if refused else "error", 0.0 if refused else -estimate, {**call, "http": e.code})
            if e.code == 401:
                fail("OpenAI refused the key (401); check the 1Password item")
            if e.code == 429:
                fail(f"rate limit or spend cap reached (429): {detail}")
            fail(f"HTTP {e.code}: {detail}")
        except OSError as e:
            log(cid, "error", 0.0, {**call, "reason": str(e)[:200]})
            fail(f"could not reach api.openai.com: {e}")
        finally:
            conn.close()
        usage = data.get("usage") or {}
        print(f"quality {quality}, size {size}, tokens in {usage.get('input_tokens', '?')} out {usage.get('output_tokens', '?')}", file=sys.stderr)
        actual, tokens = spend(usage)
        log(cid, "ok", round(actual - estimate, 5), {**call, **tokens})
        return [base64.b64decode(d["b64_json"]) for d in data["data"]]
    raise AssertionError("unreachable")


# USD per 1M tokens: text in, image in, image out (pricing page, 2026-11-13).
PRICE = (5.00, 8.00, 30.00)
# Medium output tokens, measured; low and high roughly scale.
OUT_TOKENS = {"1024x1024": 1756, "1536x1024": 1372, "1024x1536": 1372}
QUALITY_SCALE = {"low": 0.25, "medium": 1.0, "high": 4.0}
COMPRESSION = 90
EXT = {"png": "png", "jpeg": "jpg", "webp": "webp"}
LEDGER = Path(os.environ.get("OPENAI_IMAGE_LEDGER", Path.home() / ".cache" / "openai-image" / "ledger.jsonl"))


def estimate_usd(prompt: str, quality: str, size: str, n: int) -> float:
    out = OUT_TOKENS[size] * QUALITY_SCALE[quality] * n
    return round((len(prompt) / 4 * PRICE[0] + out * PRICE[2]) / 1e6, 5)


def spend(usage: dict) -> tuple[float, dict]:
    d = usage.get("input_tokens_details") or {}
    text_in = d.get("text_tokens", usage.get("input_tokens", 0) or 0)
    image_in = d.get("image_tokens", 0) or 0
    out = usage.get("output_tokens", 0) or 0
    cost = (text_in * PRICE[0] + image_in * PRICE[1] + out * PRICE[2]) / 1e6
    return cost, {"text_in": text_in, "image_in": image_in, "out": out}


def log(cid: str, status: str, usd: float, fields: dict) -> None:
    """Two lines per call share an id; summing usd gives spend.

    The sent line, written before the request, carries an estimate, so a cut-off
    or killed call still counts. The outcome line corrects it: to the true cost
    on ok, to zero on an HTTP error other than a refusal, and not otherwise.
    """
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as fh:
        fh.write(json.dumps({"t": time.time(), "id": cid, "status": status, **fields, "usd": round(usd, 5)}) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("prompt")
    ap.add_argument("--quality", choices=("low", "medium", "high"), default="medium")
    ap.add_argument("--size", choices=SIZES, default="1536x1024")
    ap.add_argument("--ref", type=Path, action="append", default=[], help="reference image to match the style of (repeatable); uses the edits endpoint")
    ap.add_argument("--format", choices=tuple(EXT), default="png", help="jpeg or webp is a far smaller response, for a proxy that cuts large ones")
    ap.add_argument("--n", type=int, default=1, help="variants from one call, saved as NAME-1.png, NAME-2.png, ...")
    ap.add_argument("--out", type=Path, help="directory to save into (default ~/Pictures/openai)")
    ap.add_argument("--name", help="file name without extension (default from the prompt and time)")
    a = ap.parse_args()
    out_dir = a.out or Path(os.environ.get("OPENAI_IMAGE_DIR", Path.home() / "Pictures" / "openai"))
    out_dir.mkdir(parents=True, exist_ok=True)
    name = a.name or (re.sub(r"[^a-z0-9]+", "-", a.prompt.lower())[-40:].strip("-") + time.strftime("-%H%M%S"))
    images = generate(a.prompt, a.quality, a.size, a.n, a.ref, a.format)
    ext = EXT[a.format]
    for i, img in enumerate(images, 1):
        path = out_dir / (f"{name}.{ext}" if len(images) == 1 else f"{name}-{i}.{ext}")
        path.write_bytes(img)
        print(f"MEDIA:{path}")


if __name__ == "__main__":
    main()
