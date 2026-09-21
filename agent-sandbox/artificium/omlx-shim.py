#!/usr/bin/env python3
"""Put Artificium's text tool-protocol back together after oMLX takes it apart.

Artificium speaks a provider-neutral protocol: the model emits
`<tool_call>{"tool": "...", ...}</tool_call>` as ordinary text, and Artificium
parses it out of `message.content` itself.

oMLX parses tool calls out of every response unconditionally
(`server.py` -> `extract_tool_calls_with_thinking`, with no setting to turn it
off). It lifts those blocks into `message.tool_calls` and hands back a
`message.content` with them removed — so Artificium sees an empty answer and
reports "The model returned an empty answer (tool_calls)". Without this shim an
Artificium run on oMLX cannot make a single successful tool call.

This is lossless in the direction that matters: oMLX gives us the tool name and
a JSON argument string, which is exactly what Artificium's format carries. It
listens on loopback inside the sandbox, so it opens no new network surface.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = os.environ.get("SHIM_UPSTREAM", "http://omlx.host:8000")
LISTEN_PORT = int(os.environ.get("SHIM_PORT", "8100"))
TIMEOUT = float(os.environ.get("SHIM_TIMEOUT", "3600"))


def render_tool_calls(tool_calls: list) -> str:
    """OpenAI tool_calls -> the text block Artificium expects to parse."""
    blocks = []
    for call in tool_calls:
        function = (call or {}).get("function") or {}
        name = function.get("name")
        if not name:
            continue
        raw = function.get("arguments")
        if isinstance(raw, str):
            try:
                args = json.loads(raw) if raw.strip() else {}
            except json.JSONDecodeError:
                # Better to hand the agent a malformed call it can see and
                # repair than to drop it silently, which is the failure this
                # whole shim exists to undo.
                args = {"_unparsed_arguments": raw}
        elif isinstance(raw, dict):
            args = raw
        else:
            args = {}
        payload = {"tool": name}
        payload.update({k: v for k, v in args.items() if k != "tool"})
        blocks.append("<tool_call>\n" + json.dumps(payload) + "\n</tool_call>")
    return "\n".join(blocks)


def restore(body: dict) -> dict:
    for choice in body.get("choices") or []:
        message = choice.get("message")
        if not isinstance(message, dict):
            continue
        calls = message.get("tool_calls")
        if not calls:
            continue
        text = render_tool_calls(calls)
        if not text:
            continue
        existing = message.get("content") or ""
        message["content"] = f"{existing}\n{text}".strip() if existing else text
        message["tool_calls"] = None
        # oMLX reports finish_reason=tool_calls; Artificium treats that as a
        # truncated generation rather than a completed turn.
        if choice.get("finish_reason") == "tool_calls":
            choice["finish_reason"] = "stop"
    return body


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # noqa: A002 - base class signature
        sys.stderr.write("shim: " + (fmt % args) + "\n")

    def _proxy(self, method: str) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        payload = self.rfile.read(length) if length else None
        url = UPSTREAM.rstrip("/") + self.path
        request = urllib.request.Request(url, data=payload, method=method)
        for header in ("Authorization", "Content-Type", "Accept"):
            value = self.headers.get(header)
            if value:
                request.add_header(header, value)
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                raw = response.read()
                status = response.status
                ctype = response.headers.get("Content-Type", "application/json")
        except urllib.error.HTTPError as err:
            raw, status = err.read(), err.code
            ctype = err.headers.get("Content-Type", "application/json")
        except Exception as err:  # upstream unreachable
            raw = json.dumps({"error": {"message": f"shim upstream: {err}"}}).encode()
            status, ctype = 502, "application/json"

        if status == 200 and "json" in ctype and self.path.endswith("/chat/completions"):
            try:
                raw = json.dumps(restore(json.loads(raw))).encode()
            except (json.JSONDecodeError, TypeError):
                pass

        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):  # noqa: N802
        self._proxy("POST")

    def do_GET(self):  # noqa: N802
        self._proxy("GET")


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", LISTEN_PORT), Handler)
    sys.stderr.write(f"shim: 127.0.0.1:{LISTEN_PORT} -> {UPSTREAM}\n")
    server.serve_forever()
