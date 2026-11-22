"""statusline-post.py against a stand-in dradis core and a stub ccstatusline."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "bin/statusline-post.py"

# Shaped like Claude Code's status-line JSON; rate_limits resets_at are unix seconds.
PAYLOAD = json.dumps(
    {
        "session_id": "abc123",
        "cwd": "/Users/x/Git/toolbox",
        "model": {"id": "claude-sonnet-5", "display_name": "Sonnet"},
        "version": "2.1.0",
        "rate_limits": {
            "five_hour": {"used_percentage": 23.5, "resets_at": 1763827200},
            "seven_day": {"used_percentage": 41.2, "resets_at": 1764345600},
        },
    }
).encode()


class Core(BaseHTTPRequestHandler):
    seen: list[dict] = []

    def do_POST(self) -> None:
        body = self.rfile.read(int(self.headers["Content-Length"]))
        Core.seen.append({"path": self.path, "body": body})
        self.send_response(204)
        self.end_headers()

    def log_message(self, *args: object) -> None:
        pass


class StatuslinePost(unittest.TestCase):
    def setUp(self) -> None:
        Core.seen = []
        self.server = HTTPServer(("127.0.0.1", 0), Core)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.url = f"http://127.0.0.1:{self.server.server_port}"

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        # A stub ccstatusline that prints a marker, then echoes its stdin.
        self.cc = self.tmp / "ccstatusline"
        self.cc.write_text("#!/bin/sh\nprintf 'STUB:'\ncat\n")
        self.cc.chmod(0o755)

    def run_script(self, url: str | None = None, stdin: bytes = PAYLOAD, stamp: str = "stamp") -> subprocess.CompletedProcess[bytes]:
        env = os.environ | {
            "DRADIS_URL": url or self.url,
            "DRADIS_HOST": "moria",
            "CCSTATUSLINE": str(self.cc),
            "STATUSLINE_POST_STAMP": str(self.tmp / stamp),
        }
        return subprocess.run([str(SCRIPT)], input=stdin, capture_output=True, env=env, check=False)

    def wait_for_posts(self, count: int) -> None:
        deadline = time.monotonic() + 5
        while len(Core.seen) < count and time.monotonic() < deadline:
            time.sleep(0.05)

    def test_posts_rate_limits_and_prints_ccstatusline_unchanged(self) -> None:
        result = self.run_script()
        self.assertEqual((result.returncode, result.stdout), (0, b"STUB:" + PAYLOAD))

        self.wait_for_posts(1)
        self.assertEqual(Core.seen[-1]["path"], "/quota/claude")
        body = json.loads(Core.seen[-1]["body"])
        self.assertEqual(body["host"], "moria")
        self.assertEqual(body["five_hour"], {"used_percentage": 23.5, "resets_at": 1763827200})
        self.assertEqual(body["seven_day"], {"used_percentage": 41.2, "resets_at": 1764345600})

    def test_posts_at_most_once_a_minute(self) -> None:
        self.run_script()
        self.wait_for_posts(1)
        self.run_script()
        time.sleep(0.5)
        self.assertEqual(len(Core.seen), 1)

    def test_no_rate_limits_means_no_post_but_still_prints(self) -> None:
        bare = b'{"session_id": "abc123"}'
        result = self.run_script(stdin=bare)
        self.assertEqual(result.stdout, b"STUB:" + bare)
        time.sleep(0.3)
        self.assertEqual(Core.seen, [])

    def test_a_refused_core_neither_fails_nor_delays(self) -> None:
        started = time.monotonic()
        result = self.run_script(url="http://127.0.0.1:9")
        self.assertLess(time.monotonic() - started, 1.5)
        self.assertEqual((result.returncode, result.stdout), (0, b"STUB:" + PAYLOAD))

    def test_a_hung_core_does_not_hold_the_status_line(self) -> None:
        # Accepts the TCP connection and never answers: the post times out in its child.
        hung = socket.socket()
        hung.bind(("127.0.0.1", 0))
        hung.listen(1)
        self.addCleanup(hung.close)
        url = f"http://127.0.0.1:{hung.getsockname()[1]}"

        started = time.monotonic()
        result = self.run_script(url=url)
        self.assertLess(time.monotonic() - started, 1.0)
        self.assertEqual((result.returncode, result.stdout), (0, b"STUB:" + PAYLOAD))


if __name__ == "__main__":
    unittest.main()
