"""dradis-hook.sh against a stand-in core that records each request."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "dot/claude/.claude/hooks/dradis-hook.sh"
REPLY = b'{"decision":"block","reason":"hi"}'


class Core(BaseHTTPRequestHandler):
    seen: list[dict] = []

    def do_POST(self) -> None:
        body = self.rfile.read(int(self.headers["Content-Length"]))
        Core.seen.append({"path": self.path, "terminal": self.headers.get("X-Hc-Terminal"), "body": body})
        self.send_response(200)
        self.end_headers()
        self.wfile.write(REPLY)

    def log_message(self, *args: object) -> None:
        pass


class DradisHook(unittest.TestCase):
    def setUp(self) -> None:
        Core.seen = []
        self.server = HTTPServer(("127.0.0.1", 0), Core)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.url = f"http://127.0.0.1:{self.server.server_port}/factory"

    def run_hook(self, event: str, host: str, terminal: str | None = "t1k", url: str | None = None):
        env = {k: v for k, v in os.environ.items() if k != "HC_TERMINAL_ID"}
        env |= {"DRADIS_URL": url or self.url, "DRADIS_HOST": host}
        if terminal:
            env["HC_TERMINAL_ID"] = terminal
        return subprocess.run([str(HOOK), event], input=b'{"session_id":"s"}', capture_output=True, env=env, check=False)

    def test_remote_terminals_carry_the_machine_prefix(self) -> None:
        for host, want in [("moria", "moriats/t1k"), ("foundation", "foundationts/t1k"), ("dungeon", "t1k")]:
            self.run_hook("UserPromptSubmit", host)
            self.assertEqual(Core.seen[-1]["terminal"], want)
            self.assertEqual(Core.seen[-1]["path"], "/factory/hooks/UserPromptSubmit")
            self.assertEqual(Core.seen[-1]["body"], b'{"session_id":"s"}')

    def test_no_terminal_sends_no_header(self) -> None:
        self.run_hook("Notification", "moria", terminal=None)
        self.assertIsNone(Core.seen[-1]["terminal"])

    def test_only_batch_and_stop_replies_reach_claude(self) -> None:
        self.assertEqual(json.loads(self.run_hook("Stop", "dungeon").stdout)["decision"], "block")
        self.assertEqual(self.run_hook("PostToolBatch", "dungeon").stdout, REPLY)
        self.assertEqual(self.run_hook("SessionStart", "dungeon").stdout, b"")

    def test_a_dead_core_passes(self) -> None:
        with tempfile.TemporaryDirectory():
            result = self.run_hook("Stop", "moria", url="http://127.0.0.1:9/factory")
        self.assertEqual((result.returncode, result.stdout), (0, b""))

    def test_wake_runs_dradis_script_with_the_prefixed_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            script = Path(home) / "hooks/wake.sh"
            script.parent.mkdir()
            script.write_text('#!/bin/sh\necho "$HC_TERMINAL_ID $DRADIS_URL"\n')
            script.chmod(0o755)
            env = os.environ | {"DRADIS_HOME": home, "DRADIS_HOST": "moria", "HC_TERMINAL_ID": "t9", "DRADIS_URL": self.url}
            out = subprocess.run([str(HOOK), "wake"], capture_output=True, env=env, check=False).stdout
        self.assertEqual(out.decode().split(), ["moriats/t9", self.url])

    def test_wake_without_a_dradis_checkout_passes(self) -> None:
        env = os.environ | {"DRADIS_HOME": "/nonexistent", "DRADIS_HOST": "foundation"}
        self.assertEqual(subprocess.run([str(HOOK), "wake"], env=env, check=False).returncode, 0)


if __name__ == "__main__":
    unittest.main()
