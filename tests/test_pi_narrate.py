"""What matters in pi-narrate is that it never loses the stream.

It sits between an unattended worker and its only log, so the failure that
would actually hurt is a formatting bug taking down a run, or a record
boundary being read wrong and silently dropping events. Both are tested here.
"""

from __future__ import annotations

import io
import json
import unittest

from _loader import load

narrate = load("pi-narrate.py")


class FakeClock:
    """Deterministic elapsed times, so assertions can talk about durations."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def make(**kwargs):
    out = io.StringIO()
    alerts = kwargs.pop("alerts", None)
    clock = kwargs.pop("clock", FakeClock())
    narrator = narrate.Narrator(
        label=kwargs.pop("label", "issue-16"),
        out=out,
        alerts=alerts,
        clock=clock,
        **kwargs,
    )
    return narrator, out, clock


def feed(narrator, *events) -> None:
    for event in events:
        narrator.feed(json.dumps(event))


class RecordFraming(unittest.TestCase):
    """pi's docs call out that a generic line reader is not protocol-compliant."""

    def test_splits_on_lf_only(self):
        stream = io.BytesIO(b'{"a":1}\n{"b":2}\n')
        self.assertEqual(list(narrate.records(stream)), [b'{"a":1}', b'{"b":2}'])

    def test_does_not_split_on_unicode_line_separators(self):
        # U+2028 and U+2029 are legal *raw* inside a JSON string and do turn up
        # in model output. pi's docs single them out: a generic line reader
        # splits on them and corrupts the record. `ensure_ascii=False` is what
        # puts the raw code point on the wire, which is what pi itself does.
        payload = json.dumps({"text": "before\u2028and\u2029after"}, ensure_ascii=False)
        self.assertIn("\u2028", payload, "the fixture must carry a raw separator, not an escape")
        records = list(narrate.records(io.BytesIO(payload.encode("utf-8") + b"\n")))
        self.assertEqual(len(records), 1, "one event, however many Unicode separators it holds")
        self.assertEqual(json.loads(records[0])["text"], "before\u2028and\u2029after")

    def test_does_not_split_on_bare_carriage_return(self):
        # Built as raw bytes on purpose. `json.dumps({"text": "a\rb"})` escapes
        # the CR, so the encoded payload holds no CR byte at all and the test
        # would pass against a reader that splits on one.
        payload = b'{"text": "a\rb"}'
        self.assertIn(b"\r", payload, "the fixture must carry a real CR byte")
        records = list(narrate.records(io.BytesIO(payload + b"\n")))
        self.assertEqual(records, [payload], "LF is the only delimiter")

    def test_yields_a_trailing_record_with_no_final_newline(self):
        records = list(narrate.records(io.BytesIO(b'{"a":1}')))
        self.assertEqual(records, [b'{"a":1}'], "a truncated log must not lose its last event")

    def test_reassembles_a_record_far_larger_than_one_read(self):
        # `agent_end` carries every message in the session and runs to megabytes
        # on a single line, so it spans many reads. The incremental-search
        # bookkeeping that keeps this from being quadratic must not lose bytes.
        big = json.dumps({"type": "agent_end", "messages": ["x" * 400_000]}).encode("utf-8")
        records = list(narrate.records(io.BytesIO(big + b"\n" + b'{"type":"agent_settled"}\n')))
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0], big, "not one byte off")
        self.assertEqual(json.loads(records[1])["type"], "agent_settled")

    def test_a_newline_split_across_two_reads_still_ends_the_record(self):
        class Trickle(io.BytesIO):
            """One byte per read, the worst case for buffered scanning."""

            def read1(self, _size=-1):  # noqa: D102
                return super().read(1)

        records = list(narrate.records(Trickle(b'{"a":1}\n{"b":2}\n')))
        self.assertEqual(records, [b'{"a":1}', b'{"b":2}'])


class Narration(unittest.TestCase):
    def test_reports_tool_calls_with_the_argument_that_identifies_them(self):
        narrator, out, _ = make()
        feed(
            narrator,
            {"type": "turn_start"},
            {
                "type": "tool_execution_start",
                "toolCallId": "c1",
                "toolName": "bash",
                "args": {"command": "godot --headless"},
            },
        )
        self.assertIn("bash godot --headless", out.getvalue())
        self.assertIn("t1", out.getvalue(), "the turn number is how you judge progress")

    def test_reports_what_the_worker_said(self):
        narrator, out, _ = make()
        feed(
            narrator,
            {
                "type": "message_update",
                "assistantMessageEvent": {"type": "text_end", "content": "Adding\n the flag."},
            },
        )
        self.assertIn("» Adding the flag.", out.getvalue())

    def test_stays_silent_about_whitespace_only_prose(self):
        narrator, out, _ = make()
        feed(
            narrator,
            {"type": "message_update", "assistantMessageEvent": {"type": "text_end", "content": "\n\n"}},
        )
        self.assertEqual(out.getvalue(), "", "models emit these constantly; they are not narration")

    def test_thinking_is_off_by_default_and_available_on_request(self):
        event = {
            "type": "message_update",
            "assistantMessageEvent": {"type": "thinking_end", "content": "let me consider"},
        }
        quiet, quiet_out, _ = make()
        feed(quiet, event)
        self.assertEqual(quiet_out.getvalue(), "")

        loud, loud_out, _ = make(show_thinking=True)
        feed(loud, event)
        self.assertIn("~ let me consider", loud_out.getvalue())

    def test_reports_a_slow_tool_finishing_but_not_a_fast_one(self):
        narrator, out, clock = make(slow_tool=20.0)
        feed(narrator, {"type": "tool_execution_start", "toolCallId": "c1", "toolName": "read"})
        clock.advance(0.2)
        feed(narrator, {"type": "tool_execution_end", "toolCallId": "c1", "toolName": "read"})
        self.assertNotIn("✓", out.getvalue(), "a 200ms read finishing is not news")

        feed(narrator, {"type": "tool_execution_start", "toolCallId": "c2", "toolName": "bash"})
        clock.advance(55)
        feed(narrator, {"type": "tool_execution_end", "toolCallId": "c2", "toolName": "bash"})
        self.assertIn("✓ bash ok (55s)", out.getvalue(), "a suite run finishing is")

    def test_reports_a_failure_with_the_reason(self):
        narrator, out, _ = make()
        feed(
            narrator,
            {
                "type": "tool_execution_end",
                "toolCallId": "c9",
                "toolName": "bash",
                "isError": True,
                "result": {"content": [{"type": "text", "text": "Never push. The orchestrator does."}]},
            },
        )
        # This is also how a guardrail block surfaces, which is the point:
        # a refused tool call looks like slowness from outside otherwise.
        self.assertIn("✗ bash FAILED", out.getvalue())
        self.assertIn("Never push.", out.getvalue())

    def test_counts_cost_across_turns_rather_than_reporting_the_last_one(self):
        narrator, out, _ = make(heartbeat=2)
        for _ in range(2):
            feed(
                narrator,
                {"type": "turn_start"},
                {"type": "turn_end", "message": {"usage": {"cost": {"total": 0.01}}}},
            )
        self.assertIn("$0.0200", out.getvalue(), "a running total, not the latest turn")

    def test_heartbeat_can_be_switched_off(self):
        narrator, out, _ = make(heartbeat=0)
        for _ in range(30):
            feed(narrator, {"type": "turn_start"}, {"type": "turn_end", "message": {}})
        self.assertNotIn("·", out.getvalue())


class Completion(unittest.TestCase):
    """Exactly one closing line per run, and the alerts monitor depends on it."""

    def test_agent_settled_is_what_finishes_a_run(self):
        # pi defines agent_settled as "no automatic retry, compaction retry, or
        # queued continuation remains". agent_end is one low-level run.
        narrator, out, _ = make()
        feed(narrator, {"type": "agent_settled"})
        self.assertIn("■ done", out.getvalue())

    def test_agent_end_alone_does_not_claim_the_run_is_over(self):
        narrator, out, _ = make()
        feed(narrator, {"type": "agent_end", "willRetry": True})
        self.assertNotIn("■", out.getvalue(), "a retry is coming; this is not completion")

    def test_a_retried_run_still_reports_completion_once(self):
        narrator, out, _ = make()
        feed(
            narrator,
            {"type": "agent_end", "willRetry": True},
            {"type": "auto_retry_start"},
            {"type": "agent_end"},
            {"type": "agent_settled"},
        )
        self.assertEqual(out.getvalue().count("■ done"), 1)

    def test_finish_is_idempotent(self):
        narrator, out, _ = make()
        narrator.finish()
        narrator.finish()
        feed(narrator, {"type": "agent_settled"})
        self.assertEqual(out.getvalue().count("■ done"), 1)

    def test_a_run_that_dies_before_settling_still_gets_a_closing_line(self):
        # Under pi-rpc.py this is what the alerts monitor sees for a crash; the
        # supervisor calls finish() when pi's stdout closes.
        narrator, out, _ = make()
        feed(narrator, {"type": "turn_start"})
        narrator.finish()
        self.assertIn("■ done — 1 turns", out.getvalue())


class Resilience(unittest.TestCase):
    def test_non_json_output_is_surfaced_rather_than_dropped(self):
        # With `2>&1` this is pi's own stderr — the settings-lock warning, a
        # provider error. Those used to vanish into the log entirely.
        narrator, out, _ = make()
        narrator.feed("Invalid settings file: EPERM: mkdir settings.json.lock")
        self.assertIn("! Invalid settings file", out.getvalue())

    def test_a_malformed_event_does_not_raise(self):
        narrator, out, _ = make()
        # `args` as a list rather than an object; `result` as something odd.
        feed(
            narrator,
            {"type": "tool_execution_start", "toolCallId": 5, "toolName": None, "args": [1, 2]},
            {"type": "tool_execution_end", "toolCallId": 5, "isError": True, "result": 7},
            {"type": "turn_end", "message": None},
        )
        self.assertNotEqual(out.getvalue(), "", "it still says something")

    def test_a_json_scalar_is_ignored_rather_than_treated_as_an_event(self):
        narrator, out, _ = make()
        narrator.feed("42")
        self.assertEqual(out.getvalue(), "")

    def test_blank_lines_are_ignored(self):
        narrator, out, _ = make()
        narrator.feed("   \n")
        self.assertEqual(out.getvalue(), "")


class Alerts(unittest.TestCase):
    """The alerts file feeds a monitor, so it must stay quiet enough to be read."""

    def test_only_alert_worthy_lines_are_written(self):
        alerts = io.StringIO()
        narrator, out, _ = make(alerts=alerts)
        feed(
            narrator,
            {"type": "turn_start"},
            {"type": "tool_execution_start", "toolCallId": "c1", "toolName": "read", "args": {"path": "a"}},
            {"type": "message_update", "assistantMessageEvent": {"type": "text_end", "content": "hi"}},
            {"type": "tool_execution_end", "toolCallId": "c1", "toolName": "read", "isError": True, "result": "boom"},
            {"type": "agent_settled"},
        )
        lines = [line for line in alerts.getvalue().splitlines() if line]
        self.assertEqual(len(lines), 2, "the failure and the completion; not the routine narration")
        self.assertIn("✗ read FAILED", lines[0])
        self.assertIn("■ done", lines[1])

    def test_narration_still_carries_everything(self):
        alerts = io.StringIO()
        narrator, out, _ = make(alerts=alerts)
        feed(
            narrator,
            {"type": "tool_execution_start", "toolCallId": "c1", "toolName": "read", "args": {"path": "a"}},
        )
        self.assertIn("▸ read a", out.getvalue())
        self.assertEqual(alerts.getvalue(), "")


class Formatting(unittest.TestCase):
    def test_elapsed_reads_as_a_duration_not_a_float(self):
        self.assertEqual(narrate.elapsed(9), "9s")
        self.assertEqual(narrate.elapsed(372), "6m12s")
        self.assertEqual(narrate.elapsed(7325), "2h02m")

    def test_lines_are_truncated_so_a_status_row_stays_one_row(self):
        narrator, out, _ = make(width=60)
        feed(
            narrator,
            {
                "type": "message_update",
                "assistantMessageEvent": {"type": "text_end", "content": "x" * 500},
            },
        )
        self.assertEqual(len(out.getvalue().rstrip("\n")), 60)

    def test_result_text_prefers_the_readable_part(self):
        self.assertEqual(
            narrate.result_text({"content": [{"type": "text", "text": "a\nb"}]}),
            "a b",
        )
        self.assertEqual(narrate.result_text("plain"), "plain")
        self.assertEqual(narrate.result_text(None), "")


if __name__ == "__main__":
    unittest.main()
