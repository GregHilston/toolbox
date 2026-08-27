"""Replay a real pi session through the narrator.

Every other narrator test asserts against event shapes this repo made up. They
are self-consistent — narrator, extension and tests all agree — and all three
would be wrong together if pi's schema moved. `fixtures/real-pi-session.jsonl`
is an actual `pi --mode json` run, captured 2026-08-27 on pi 0.84.3 (paths
normalised, nothing else changed), so it pins the shapes to something outside
our own assumptions.

If a pi upgrade renames a field, this is the test that notices. Recapture with:

    pi --mode json -p 'Run `echo hello` with the bash tool, then reply DONE.' \\
      > tests/fixtures/real-pi-session.jsonl

then normalise absolute paths out of it and update the assertions below to the
new session's actual tool call and reply.
"""

from __future__ import annotations

import io
import json
import unittest
from pathlib import Path

from _loader import load

narrate = load("pi-narrate.py")

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "real-pi-session.jsonl"


def replay(**kwargs) -> str:
    out = io.StringIO()
    narrator = narrate.Narrator(label="issue-77", out=out, **kwargs)
    with open(FIXTURE, "rb") as handle:
        for record in narrate.records(handle):
            narrator.feed(record.decode("utf-8"))
    narrator.finish()
    return out.getvalue()


class RealStream(unittest.TestCase):
    def test_the_fixture_is_a_real_session_and_not_a_hand_written_one(self):
        types = set()
        for line in FIXTURE.read_text().splitlines():
            if line.strip():
                types.add(json.loads(line)["type"])
        # The delta events are the ones nobody would write by hand, and the
        # ones a schema change is most likely to touch.
        for required in ("session", "agent_start", "turn_start", "message_update",
                         "tool_execution_start", "tool_execution_end", "turn_end",
                         "agent_end", "agent_settled"):
            self.assertIn(required, types, f"{required} missing; is the capture truncated?")

    def test_a_real_session_narrates_end_to_end(self):
        narration = replay()
        lines = narration.splitlines()
        self.assertIn("○ session", lines[0])
        self.assertIn("/repo/worktrees/issue-77", lines[0], "the cwd, read off the real header")
        self.assertIn("▸ bash echo hello", narration, "the tool call and its real argument")
        self.assertIn("» DONE", narration, "what the model actually said")
        self.assertIn("■ done", narration)

    def test_the_turn_count_matches_the_session(self):
        # Two turn_start events in the capture.
        self.assertRegex(replay(), r"done — 2 turns, 1 tools, 0 failed")

    def test_thinking_is_narrated_only_when_asked(self):
        self.assertNotIn("~ ", replay())
        self.assertIn("~ ", replay(show_thinking=True), "the capture does contain reasoning")

    def test_only_the_completion_reaches_the_alerts_file(self):
        alerts = io.StringIO()
        replay(alerts=alerts)
        lines = [line for line in alerts.getvalue().splitlines() if line]
        self.assertEqual(len(lines), 1, "a clean run is one alert: it finished")
        self.assertIn("■ done", lines[0])

    def test_replaying_twice_is_deterministic(self):
        first = [line.split(None, 3)[-1] for line in replay().splitlines()]
        second = [line.split(None, 3)[-1] for line in replay().splitlines()]
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
