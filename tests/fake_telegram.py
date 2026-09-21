"""A stand-in for api.telegram.org, for testing `bin/agent-telegram.py`'s loop.

`tests/fake_pi.py` exists for the same reason: every serious defect in a script
like this lives in the transport loop -- offsets that do not advance, a restart
that replays a stale command, an allowlist checked after the side effect -- and
none of that is reachable by testing pure functions.

Serves the two methods the bot uses and records what it was asked to send.
Queued batches are handed out one `getUpdates` at a time, so a test can say
"these updates were already waiting when the bot started, these arrived after".
"""

from __future__ import annotations

import json
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer


class FakeTelegram:
    def __init__(self, batches: list[list[dict]]) -> None:
        self.batches = list(batches)
        self.sent: list[tuple[int, str]] = []
        self.offsets: list[int | None] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):  # keep the test output readable
                pass

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length).decode()
                params = {k: v[0] for k, v in urllib.parse.parse_qs(body).items()}
                method = self.path.rsplit("/", 1)[-1]

                if method == "getUpdates":
                    off = params.get("offset")
                    outer.offsets.append(int(off) if off is not None else None)
                    result = outer.batches.pop(0) if outer.batches else []
                elif method == "sendMessage":
                    outer.sent.append((int(params["chat_id"]), params["text"]))
                    result = {"message_id": len(outer.sent)}
                else:  # pragma: no cover - the bot uses no other method
                    result = {}

                payload = json.dumps({"ok": True, "result": result}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def __enter__(self) -> "FakeTelegram":
        self.thread.start()
        return self

    def __exit__(self, *_exc) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def message(update_id: int, chat_id: int, text: str) -> dict:
    return {
        "update_id": update_id,
        "message": {"message_id": update_id, "chat": {"id": chat_id}, "text": text},
    }
