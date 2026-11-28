"""openai-image.py against a fake Images API on a local port; no paid calls.

What a caller relies on: a cut-off response is retried once and no more, every
call reaches the ledger before it is sent, and a refusal still reads as one.
"""

from __future__ import annotations

import base64
import contextlib
import io
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar

from _loader import load

oi = load("openai-image.py")
IMAGE = b"\xff\xd8\xff\xe0fake-jpeg"
USAGE = {"input_tokens": 190, "input_tokens_details": {"text_tokens": 190}, "output_tokens": 1756}


class FakeOpenAI(BaseHTTPRequestHandler):
    modes: ClassVar[list[str]] = []  # one per request: ok | cut | refuse | down
    bodies: ClassVar[list[dict]] = []

    def log_message(self, *args):
        pass

    def do_POST(self):
        FakeOpenAI.bodies.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
        mode = FakeOpenAI.modes.pop(0)
        if mode == "refuse":
            data = json.dumps({"error": {"code": "moderation_blocked", "message": "safety_violations=[illicit]"}}).encode()
            return self.send(400, data, len(data))
        if mode == "down":
            data = b'{"error": "server"}'
            return self.send(500, data, len(data))
        data = json.dumps({"data": [{"b64_json": base64.b64encode(IMAGE).decode()}], "usage": USAGE}).encode()
        self.send(200, data, len(data) + (40_000 if mode == "cut" else 0))

    def send(self, code, data, length):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        self.wfile.write(data)
        self.close_connection = True


class OpenAIImageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOpenAI)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        FakeOpenAI.bodies.clear()
        self.saved = (oi.URL, oi.LEDGER, os.environ.get("OPENAI_API_KEY"))
        oi.URL = f"http://127.0.0.1:{self.server.server_port}/v1/images/generations"
        oi.LEDGER = self.tmp / "ledger.jsonl"
        os.environ["OPENAI_API_KEY"] = "test-key"

    def tearDown(self):
        oi.URL, oi.LEDGER, key = self.saved
        if key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = key

    def run_gen(self, *modes, fmt="jpeg"):
        FakeOpenAI.modes[:] = list(modes)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            try:
                return oi.generate("a toy blaster", "medium", "1024x1024", 1, [], fmt), err.getvalue()
            except SystemExit:
                return None, err.getvalue()

    def ledger(self):
        return [json.loads(line) for line in oi.LEDGER.read_text().splitlines()]

    def test_asks_for_compressed_output(self):
        images, _ = self.run_gen("ok")
        self.assertEqual(images, [IMAGE])
        self.assertEqual(FakeOpenAI.bodies[0]["output_format"], "jpeg")
        self.assertEqual(FakeOpenAI.bodies[0]["output_compression"], oi.COMPRESSION)

    def test_png_sends_no_compression(self):
        self.run_gen("ok", fmt="png")
        self.assertNotIn("output_compression", FakeOpenAI.bodies[0])

    def test_ok_sums_to_true_cost(self):
        self.run_gen("ok")
        rows = self.ledger()
        self.assertEqual([r["status"] for r in rows], ["sent", "ok"])
        self.assertEqual(rows[0]["id"], rows[1]["id"])
        true_cost = (190 * oi.PRICE[0] + 1756 * oi.PRICE[2]) / 1e6
        self.assertAlmostEqual(sum(r["usd"] for r in rows), true_cost, places=4)

    def test_cut_response_retries_once_then_succeeds(self):
        images, err = self.run_gen("cut", "ok")
        self.assertEqual(images, [IMAGE])
        self.assertIn("retrying once", err)
        self.assertEqual([r["status"] for r in self.ledger()], ["sent", "truncated", "sent", "ok"])

    def test_cut_twice_stops_and_counts_both(self):
        images, err = self.run_gen("cut", "cut", "ok")
        self.assertIsNone(images)
        self.assertEqual(len(FakeOpenAI.bodies), 2)
        self.assertIn("cut off twice", err)
        rows = self.ledger()
        self.assertEqual([r["status"] for r in rows], ["sent", "truncated", "sent", "truncated"])
        estimate = oi.estimate_usd("a toy blaster", "medium", "1024x1024", 1)
        self.assertAlmostEqual(sum(r["usd"] for r in rows), 2 * estimate, places=5)

    def test_refusal_reads_as_one_and_stays_counted(self):
        images, err = self.run_gen("refuse")
        self.assertIsNone(images)
        self.assertIn("HTTP 400", err)
        self.assertIn("safety_violations", err)
        self.assertEqual(len(FakeOpenAI.bodies), 1)
        rows = self.ledger()
        self.assertEqual([r["status"] for r in rows], ["sent", "refused"])
        self.assertGreater(sum(r["usd"] for r in rows), 0)

    def test_server_error_is_not_retried_and_not_counted(self):
        images, _ = self.run_gen("down")
        self.assertIsNone(images)
        self.assertEqual(len(FakeOpenAI.bodies), 1)
        rows = self.ledger()
        self.assertEqual([r["status"] for r in rows], ["sent", "error"])
        self.assertAlmostEqual(sum(r["usd"] for r in rows), 0, places=6)


if __name__ == "__main__":
    unittest.main()
