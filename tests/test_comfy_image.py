"""comfy-image.py against a fake ComfyUI API on a local port.

What a bot relies on: the image lands where it can attach it, the reply carries
the prompt and seed a follow-up needs, and a sleeping moria or a failed render
reads as such instead of a traceback.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar

SCRIPT = Path(__file__).resolve().parent.parent / "bin" / "comfy-image.py"
PNG = b"\x89PNG\r\n\x1a\nfake"


class FakeComfy(BaseHTTPRequestHandler):
    mode = "ok"  # ok | error | asleep
    submitted: ClassVar[list[dict]] = []

    def log_message(self, *args):
        pass

    def reply(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.mode == "asleep":
            return self.reply(503, b"This runs on moria, which is asleep", "text/plain")
        FakeComfy.submitted.append(body["prompt"])
        self.reply(200, {"prompt_id": "p1"})

    def do_GET(self):
        if self.path.startswith("/api/history/"):
            if self.mode == "error":
                status = {"status_str": "error", "messages": [["execution_error", {"exception_message": "out of memory"}]]}
                return self.reply(200, {"p1": {"status": status, "outputs": {}}})
            image = {"filename": "agent_00001_.png", "subfolder": "", "type": "output"}
            return self.reply(200, {"p1": {"status": {"status_str": "success"}, "outputs": {"13": {"images": [image]}}}})
        if self.path.startswith("/api/view?"):
            return self.reply(200, PNG, "image/png")
        self.reply(404, {})


class TestComfyImage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeComfy)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        FakeComfy.mode = "ok"
        FakeComfy.submitted.clear()
        self.out = Path(tempfile.mkdtemp())

    def run_tool(self, *args, url=None):
        env = {"COMFY_URL": url or self.url, "HOME": str(self.out), "PATH": "/usr/bin:/bin"}
        return subprocess.run([sys.executable, str(SCRIPT), "--out", str(self.out), *args],
                              env=env, capture_output=True, text=True, timeout=30, check=False)

    def test_saves_the_image_and_prints_what_a_follow_up_needs(self):
        r = self.run_tool("--seed", "42", "two zebras playing basketball")
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.splitlines()
        self.assertEqual(lines[0], "prompt: two zebras playing basketball")
        self.assertIn("seed: 42", lines[1])
        self.assertTrue(lines[-1].startswith(f"MEDIA:{self.out}/comfy-"))
        self.assertEqual(Path(lines[-1][len("MEDIA:"):]).read_bytes(), PNG)
        wf = FakeComfy.submitted[0]
        self.assertEqual(wf["4"]["inputs"]["text"], "two zebras playing basketball")
        self.assertEqual(wf["9"]["inputs"]["noise_seed"], 42)

    def test_size_reaches_the_workflow_and_bad_sizes_are_refused(self):
        r = self.run_tool("--width", "1344", "--height", "768", "x")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(FakeComfy.submitted[0]["10"]["inputs"]["width"], 1344)
        bad = self.run_tool("--width", "1000", "x")
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn("multiples of 16", bad.stderr)

    def test_a_sleeping_moria_says_so(self):
        FakeComfy.mode = "asleep"
        r = self.run_tool("x")
        self.assertEqual(r.returncode, 1)
        self.assertIn("moria", r.stderr)
        self.assertIn("asleep", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_an_unreachable_server_says_so(self):
        r = self.run_tool("x", url="http://127.0.0.1:9")
        self.assertEqual(r.returncode, 1)
        self.assertIn("cannot reach ComfyUI", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_a_failed_render_reports_the_reason(self):
        FakeComfy.mode = "error"
        r = self.run_tool("x")
        self.assertEqual(r.returncode, 1)
        self.assertIn("out of memory", r.stderr)


if __name__ == "__main__":
    unittest.main()
