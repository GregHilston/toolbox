"""omlx-textfile.py folds profiles, survives a sleeping or broken host, and writes only numbers."""

from __future__ import annotations

import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load

mod = load("omlx-textfile.py")

STATUS = {
    "model_memory_used": 21422314484,
    "model_memory_max": 28991029248,
    "active_requests": 1,
    "waiting_requests": False,
    "avg_generation_tps": 50.2,
    "avg_prefill_tps": "n/a",
    "total_requests": 4195,
    "total_prompt_tokens": 480239,
    "total_completion_tokens": 68775,
    "total_cached_tokens": 147640,
}
MODELS = {
    "models": [
        {"id": "Qwen3.6-35B-A3B-4bit", "loaded": True, "resident_estimated_size": 21422314484, "last_access": 1791119315.4},
        {"id": "Qwen3.6-35B-A3B-4bit:lab", "source_model_id": "Qwen3.6-35B-A3B-4bit", "loaded": True},
        {"id": "Qwen3.8-27B-4bit", "loaded": False, "is_loading": True, "estimated_size": 15000000000, "last_access": None},
    ]
}
SAMPLE = re.compile(r'^[a-z_]+\{[^}]*\} -?[0-9.e+]+$')


class TestOmlxTextfile(unittest.TestCase):
    def setUp(self):
        self.prom = mod.render({"dungeon": mod.server_lines("dungeon", STATUS, MODELS), "moria": None})

    def test_a_profile_is_not_a_second_model(self):
        self.assertNotIn(":lab", self.prom)
        self.assertIn('omlx_model_memory_bytes{server="dungeon",model="Qwen3.6-35B-A3B-4bit"} 21422314484', self.prom)

    def test_an_unloaded_model_reports_no_memory(self):
        self.assertIn('omlx_model_loaded{server="dungeon",model="Qwen3.8-27B-4bit"} 0', self.prom)
        self.assertIn('omlx_model_loading{server="dungeon",model="Qwen3.8-27B-4bit"} 1', self.prom)
        self.assertNotIn('omlx_model_memory_bytes{server="dungeon",model="Qwen3.8-27B-4bit"}', self.prom)

    def test_a_sleeping_server_is_down_not_missing(self):
        self.assertIn('omlx_up{server="moria"} 0', self.prom)
        self.assertIn('omlx_up{server="dungeon"} 1', self.prom)
        self.assertNotIn('server="moria",', self.prom)

    def test_every_sample_is_a_number(self):
        for line in self.prom.splitlines():
            if not line.startswith("#"):
                self.assertRegex(line, SAMPLE)
        self.assertNotIn("omlx_waiting_requests", self.prom)
        self.assertNotIn("omlx_prefill_tokens_per_second", self.prom)

    def test_each_metric_has_one_type_line(self):
        types = [line for line in self.prom.splitlines() if line.startswith("# TYPE")]
        self.assertEqual(len(types), len(set(types)))
        self.assertIn("# TYPE omlx_requests_total counter", self.prom)

    def test_a_changed_payload_marks_that_server_down_and_keeps_the_rest(self):
        def fetch(base, path, key, timeout):
            if "100.115" in base:
                return [] if path == "/api/status" else {"models": None}
            if "100.93" in base:
                raise OSError("timed out")
            return STATUS if path == "/api/status" else MODELS

        with tempfile.TemporaryDirectory() as tmp:
            settings = Path(tmp, ".omlx", "settings.json")
            settings.parent.mkdir()
            settings.write_text(json.dumps({"auth": {"api_key": "k"}}))
            env = {"HOME": tmp, "NODE_EXPORTER_TEXTFILE_DIR": tmp + "/out"}
            with mock.patch.dict(os.environ, env), mock.patch.object(mod, "fetch", fetch), \
                    mock.patch.object(Path, "home", return_value=Path(tmp)), \
                    mock.patch("sys.stderr") as stderr:
                mod.main()
            prom = Path(tmp, "out", "omlx.prom").read_text()
            self.assertEqual(sorted(p.name for p in Path(tmp, "out").iterdir()), ["omlx.prom"])
        self.assertIn('omlx_up{server="dungeon"} 1', prom)
        self.assertIn('omlx_up{server="moria"} 0', prom)
        self.assertIn('omlx_up{server="citadel"} 0', prom)
        logged = "".join(str(c.args) for c in stderr.write.call_args_list)
        self.assertIn("moria", logged)
        self.assertNotIn("citadel", logged, "a sleeping host should not log every minute")

    def test_unreadable_settings_still_write_every_server_down(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"NODE_EXPORTER_TEXTFILE_DIR": tmp}), \
                    mock.patch.object(Path, "home", return_value=Path(tmp)), mock.patch("sys.stderr"):
                mod.main()
            prom = Path(tmp, "omlx.prom").read_text()
        for server in mod.SERVERS:
            self.assertIn(f'omlx_up{{server="{server}"}} 0', prom)


if __name__ == "__main__":
    unittest.main()
