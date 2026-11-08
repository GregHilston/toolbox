"""usage-mark.py: transcript dedup and counter-delta arithmetic on fixture data."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load

um = load("usage-mark.py")


def line(mid: str, model: str, ts: str, **usage: int) -> str:
    return json.dumps({"timestamp": ts, "message": {"id": mid, "model": model, "usage": usage}})


class ClaudeUsage(unittest.TestCase):
    def test_streamed_message_counts_once_and_old_entries_drop(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "p").mkdir()
            (root / "p" / "s" / "subagents").mkdir(parents=True)
            (root / "p" / "a.jsonl").write_text("\n".join([
                line("m1", "claude-opus", "2026-10-31T10:00:00Z", input_tokens=5, output_tokens=1),
                line("m1", "claude-opus", "2026-10-31T10:00:01Z", input_tokens=5, output_tokens=40, cache_read_input_tokens=100),
                line("old", "claude-opus", "2026-10-31T08:00:00Z", output_tokens=999),
            ]))
            (root / "p" / "s" / "subagents" / "b.jsonl").write_text(
                line("m2", "claude-haiku", "2026-10-31T10:05:00Z", output_tokens=7, cache_creation_input_tokens=3)
            )
            since = um.parse_ts("2026-10-31T09:00:00Z")
            got = um.claude_usage(root, since)
        self.assertEqual(got["claude-opus"], {"in": 5, "out": 40, "cread": 100, "cwrite": 0})
        self.assertEqual(got["claude-haiku"]["cwrite"], 3)


class Deltas(unittest.TestCase):
    def test_delta_and_counter_reset(self) -> None:
        base = {"deepseek-flash": {"total_in": 100.0, "cread": 40.0, "out": 10.0, "spend": 1.0}}
        now = {"deepseek-flash": {"total_in": 250.0, "cread": 10.0, "out": 30.0, "spend": 1.5}}
        d = um.counter_delta(now, base)["deepseek-flash"]
        self.assertEqual((d["total_in"], d["cread"], d["out"], d["spend"]), (150.0, 10.0, 20.0, 0.5))

    def test_rows_split_go_from_api_and_estimate_go_cost(self) -> None:
        delta = {
            um.GO_MODEL: {"total_in": 1_000_000.0, "cread": 400_000.0, "out": 100_000.0, "spend": 0.0},
            "deepseek-flash": {"total_in": 10.0, "cread": 4.0, "out": 2.0, "spend": 0.25},
        }
        rows = um.deepseek_rows(delta, peak=False)
        self.assertEqual(rows["Go"]["in"], 600_000)
        self.assertTrue(rows["Go"]["est"])
        self.assertAlmostEqual(rows["Go"]["cost"], (400_000 * 0.003 + 600_000 * 0.15 + 100_000 * 0.60) / 1e6)
        self.assertEqual(rows["DS API"]["cost"], 0.25)
        self.assertFalse(rows["DS API"]["est"])

    def test_fmt(self) -> None:
        self.assertEqual((um.fmt(950), um.fmt(1200), um.fmt(3_400_000), um.fmt(None)), ("950", "1.2k", "3.4M", "?"))



class Luna(unittest.TestCase):

    def test_luna_gets_its_own_row_at_no_cost(self) -> None:
        rows = um.deepseek_rows({"gpt-5.6-luna": {"total_in": 1000, "cread": 400, "out": 50, "spend": 0.0}}, peak=False)
        assert set(rows) == {"Luna"}, f"rows {set(rows)}, want Luna only"
        assert rows["Luna"]["cost"] == 0.0 and not rows["Luna"]["est"], f"Luna {rows['Luna']}, want cost 0 not estimated"
        assert rows["Luna"]["in"] == 600, f"Luna in {rows['Luna']['in']}, want 600"


    def test_render_shows_the_luna_quota(self) -> None:
        mark = {"t": 0, "gauges": {"balance": 5.0}}
        rep = um.build("x", mark, {}, {"Luna": {"in": 1, "out": 1, "cread": 1, "cwrite": None, "cost": 0.0, "est": False}},
                       {"balance": 5.0, "luna_5h": 3.0, "luna_weekly": 0.0}, [], peak=False)
        out = um.render(rep)
        assert "| Luna |" in out, f"no Luna row in:\n{out}"
        assert "Luna quota 5h 3% / wk 0%" in out, f"no Luna quota line in:\n{out}"


if __name__ == "__main__":
    unittest.main()
