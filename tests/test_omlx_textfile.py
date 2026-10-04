"""omlx-textfile.py folds profiles into their base model and survives a sleeping moria."""

from __future__ import annotations

import unittest

from _loader import load

render = load("omlx-textfile.py").render

STATUS = {
    "model_memory_used": 21422314484,
    "model_memory_max": 28991029248,
    "active_requests": 1,
    "waiting_requests": 0,
    "avg_generation_tps": 50.2,
    "avg_prefill_tps": 231.3,
    "total_requests": 4195,
    "total_prompt_tokens": 480239,
    "total_completion_tokens": 68775,
    "total_cached_tokens": 147640,
}
MODELS = {
    "models": [
        {"id": "Qwen3.6-35B-A3B-4bit", "loaded": True, "resident_estimated_size": 21422314484, "last_access": 1791119315.4},
        {"id": "Qwen3.6-35B-A3B-4bit:lab", "source_model_id": "Qwen3.6-35B-A3B-4bit", "loaded": True},
        {"id": "Qwen3.8-27B-4bit", "loaded": False, "estimated_size": 15000000000},
    ]
}


class TestOmlxTextfile(unittest.TestCase):
    def setUp(self):
        self.prom = render({"dungeon": (STATUS, MODELS), "moria": None})

    def test_a_profile_is_not_a_second_model(self):
        self.assertNotIn(":lab", self.prom)
        self.assertIn('omlx_model_memory_bytes{server="dungeon",model="Qwen3.6-35B-A3B-4bit"} 21422314484', self.prom)

    def test_an_unloaded_model_reports_no_memory(self):
        self.assertIn('omlx_model_loaded{server="dungeon",model="Qwen3.8-27B-4bit"} 0', self.prom)
        self.assertNotIn('omlx_model_memory_bytes{server="dungeon",model="Qwen3.8-27B-4bit"}', self.prom)

    def test_a_sleeping_server_is_down_not_missing(self):
        self.assertIn('omlx_up{server="moria"} 0', self.prom)
        self.assertIn('omlx_up{server="dungeon"} 1', self.prom)
        self.assertNotIn('server="moria",', self.prom)

    def test_each_metric_has_one_type_line(self):
        types = [line for line in self.prom.splitlines() if line.startswith("# TYPE")]
        self.assertEqual(len(types), len(set(types)))
        self.assertIn("# TYPE omlx_requests_total counter", self.prom)


if __name__ == "__main__":
    unittest.main()
