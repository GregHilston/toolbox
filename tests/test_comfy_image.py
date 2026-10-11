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
    mode = "ok"  # ok | error | asleep | asleep_later | not_json | no_image | slow
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
        if self.mode == "not_json":
            return self.reply(200, b"<html>captive portal</html>", "text/html")
        FakeComfy.submitted.append(body["prompt"])
        self.reply(200, {"prompt_id": "p1"})

    def do_GET(self):
        if self.path.startswith("/api/history/"):
            if self.mode == "asleep_later":
                return self.reply(503, b"asleep", "text/plain")
            if self.mode == "slow":
                return self.reply(200, {})
            if self.mode == "no_image":
                return self.reply(200, {"p1": {"status": {"status_str": "success"}, "outputs": {}}})
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

    def run_tool(self, *args, url=None, out=True, **env_extra):
        env = {"COMFY_URL": url or self.url, "HOME": str(self.out), "PATH": "/usr/bin:/bin", **env_extra}
        cmd = [sys.executable, str(SCRIPT), *(["--out", str(self.out)] if out else []), *args]
        return subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=30, check=False)

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

    def assert_plain_error(self, r, *needles):
        self.assertEqual(r.returncode, 1)
        for n in needles:
            self.assertIn(n, r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_moria_falling_asleep_mid_render_says_so(self):
        FakeComfy.mode = "asleep_later"
        self.assert_plain_error(self.run_tool("x"), "asleep")

    def test_a_non_json_page_says_so(self):
        FakeComfy.mode = "not_json"
        self.assert_plain_error(self.run_tool("x"), "other than JSON", "captive portal")

    def test_a_render_with_no_image_says_so(self):
        FakeComfy.mode = "no_image"
        self.assert_plain_error(self.run_tool("x"), "returned no image")

    def test_a_render_that_never_finishes_times_out(self):
        FakeComfy.mode = "slow"
        self.assert_plain_error(self.run_tool("x", COMFY_TIMEOUT="1"), "no image after 1s")

    def test_comfy_image_dir_is_where_it_saves_without_out(self):
        target = self.out / "cache"
        r = self.run_tool("x", out=False, COMFY_IMAGE_DIR=str(target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.splitlines()[-1].startswith(f"MEDIA:{target}/comfy-"))


if __name__ == "__main__":
    unittest.main()
