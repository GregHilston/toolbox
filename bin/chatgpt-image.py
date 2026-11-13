#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Generate an image with ChatGPT's image model on Greg's Plus plan, headless, and save it.

It calls the Codex Responses endpoint with the `image_generation` tool, signed in with
the LLM gateway's ChatGPT login on dungeon, so it costs nothing beyond Plus. Off dungeon
it reads that login over `ssh dungeon` and keeps it in memory. It never refreshes the
token: refresh tokens rotate, and LiteLLM's usage poller owns the refresh.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import NoReturn

AUTH = "~/.config/litellm-chatgpt/auth.json"
URL = "https://chatgpt.com/backend-api/codex/responses"
MODEL = "gpt-5.6-luna"
SIZES = ("auto", "1024x1024", "1536x1024", "1024x1536")


def fail(msg: str) -> NoReturn:
    print(f"chatgpt-image: {msg}", file=sys.stderr)
    sys.exit(1)


def load_auth() -> dict:
    local = Path(os.path.expanduser(AUTH))
    if local.is_file():
        return json.loads(local.read_text())
    if socket.gethostname().split(".")[0] == "dungeon":
        fail(f"no ChatGPT login at {AUTH}; see home-lab docs/runbooks/llm-chatgpt-login.md")
    r = subprocess.run(["ssh", "dungeon", f"cat {AUTH}"], capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        fail(f"could not read the ChatGPT login from dungeon: {r.stderr.strip() or 'ssh failed'}")
    return json.loads(r.stdout)


def generate(prompt: str, size: str) -> bytes:
    auth = load_auth()
    if auth.get("expires_at", 0) and auth["expires_at"] < time.time():
        fail("the ChatGPT access token has expired; the gateway's usage poller refreshes it every 5 minutes, so check that LiteLLM is up on dungeon")
    tool = {"type": "image_generation"}
    if size != "auto":
        tool["size"] = size
    body = {
        "model": MODEL,
        "instructions": "Generate exactly one image with the image_generation tool, following the prompt closely. Reply with no text.",
        "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        "tools": [tool],
        "tool_choice": "auto",
        "stream": True,
        "store": False,
    }
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers={
        "Authorization": "Bearer " + auth["access_token"],
        "chatgpt-account-id": auth["account_id"],
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "OpenAI-Beta": "responses=experimental",
        "originator": "codex_cli_rs",
    })
    try:
        resp = urllib.request.urlopen(req, timeout=300)
    except urllib.error.HTTPError as e:
        detail = e.read()[:300].decode(errors="replace")
        if e.code == 401:
            fail("ChatGPT refused the login (401); sign in again: home-lab docs/runbooks/llm-chatgpt-login.md")
        if e.code == 429:
            fail(f"the Plus allowance is used up for now (429): {detail}")
        fail(f"HTTP {e.code}: {detail}")
    except urllib.error.URLError as e:
        fail(f"could not reach chatgpt.com: {e.reason}")
    for raw in resp:
        line = raw.decode(errors="replace").strip()
        if not line.startswith("data:"):
            continue
        try:
            ev = json.loads(line[5:])
        except ValueError:
            continue
        item = ev.get("item") or {}
        if item.get("type") == "image_generation_call" and item.get("result"):
            return base64.b64decode(item["result"])
        if ev.get("type") in ("response.failed", "error"):
            fail(f"generation failed: {json.dumps(ev)[:300]}")
    fail("the response ended without an image (the model may have answered in text instead)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("prompt")
    ap.add_argument("--size", choices=SIZES, default="auto")
    ap.add_argument("--out", type=Path, help="directory to save into (default ~/Pictures/chatgpt)")
    ap.add_argument("--name", help="file name without .png (default from the prompt and time)")
    a = ap.parse_args()
    out_dir = a.out or Path(os.environ.get("CHATGPT_IMAGE_DIR", Path.home() / "Pictures" / "chatgpt"))
    out_dir.mkdir(parents=True, exist_ok=True)
    name = a.name or (re.sub(r"[^a-z0-9]+", "-", a.prompt.lower())[-40:].strip("-") + time.strftime("-%H%M%S"))
    path = out_dir / f"{name}.png"
    path.write_bytes(generate(a.prompt, a.size))
    print(f"MEDIA:{path}")


if __name__ == "__main__":
    main()
