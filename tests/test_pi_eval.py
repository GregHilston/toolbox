"""pi-eval's check logic against a fixture transcript; no pi, no network."""

from __future__ import annotations

import json
import unittest

from _loader import load

pe = load("pi-eval.py")


def tc(name, **args):
    return {"type": "toolCall", "name": name, "arguments": args}


def assistant(*content, stop="toolUse"):
    return {"role": "assistant", "content": list(content), "stopReason": stop}


MESSAGES = [
    {"role": "user", "content": [{"type": "text", "text": "is sabnzbd down?"}]},
    assistant(tc("read", path="/Users/g/.claude/skills/lab-alerts/SKILL.md")),
    {"role": "toolResult", "content": [{"type": "text", "text": "..."}]},
    assistant(tc("bash", command="curl -sS https://sabnzbd.grehg2.xyz")),
    {"role": "toolResult", "content": [{"type": "text", "text": "200"}]},
    assistant({"type": "text", "text": "Sabnzbd is up (HTTP 200)."}, stop="stop"),
]
LINES = [
    "not json",
    json.dumps({"type": "agent_start"}),
    json.dumps({"type": "agent_end", "messages": MESSAGES}),
]
T = pe.parse_transcript(LINES)


def check(**case):
    return pe.evaluate(T, 10, case)


class TestParse(unittest.TestCase):
    def test_reduces_stream(self):
        self.assertEqual(T["turns"], 3)
        self.assertEqual([c["name"] for c in T["calls"]], ["read", "bash"])
        self.assertEqual(T["answer"], "Sabnzbd is up (HTTP 200).")

    def test_missing_agent_end_fails(self):
        t = pe.parse_transcript(['{"type":"agent_start"}'])
        self.assertEqual(pe.evaluate(t, 1, {}), ["pi produced no agent_end"])

    def test_error_stop_reason_fails(self):
        m = [assistant(stop="error")]
        t = pe.parse_transcript([json.dumps({"type": "agent_end", "messages": m})])
        self.assertTrue(pe.evaluate(t, 1, {}))


class TestChecks(unittest.TestCase):
    def test_passes(self):
        self.assertEqual(
            check(
                uses_tool=["bash"], not_tool=["web_search"],
                bash_matches=[r"curl.*grehg2\.xyz"], reads_skill=["lab-alerts"],
                answer_matches=["(?i)up"], answer_not_matches=["down!"],
                calls_match=[r"read .*SKILL\.md"], max_turns=3, max_seconds=10,
            ),
            [],
        )

    def test_each_failure_reports(self):
        fails = check(
            uses_tool=["grep"], not_tool=["bash"], bash_matches=["netcheck"],
            not_bash_matches=["curl"], reads_skill=["weather"],
            answer_matches=["Gourmia"], answer_not_matches=["Sabnzbd"],
            calls_match=["ssh"], max_turns=2, max_seconds=5,
        )
        self.assertEqual(len(fails), 10)

    def test_skill_name_must_be_a_whole_path_segment(self):
        self.assertTrue(check(reads_skill=["alerts"]))

    def test_commit_is_always_forbidden(self):
        t = pe.parse_transcript([json.dumps({"type": "agent_end", "messages": [
            assistant(tc("bash", command="git commit -m x")),
            assistant({"type": "text", "text": "done"}, stop="stop"),
        ]})])
        self.assertTrue(pe.evaluate(t, 1, {}))


class TestCases(unittest.TestCase):
    def test_shipped_cases_are_valid(self):
        import tomllib
        cases = tomllib.loads(pe.CASES.read_text())["case"]
        names = [c["name"] for c in cases]
        self.assertEqual(len(names), len(set(names)))
        known = {"name", "cwd", "prompt", "uses_tool", "not_tool", "bash_matches",
                 "not_bash_matches", "calls_match", "reads_skill", "answer_matches",
                 "answer_not_matches", "max_turns", "max_seconds"}
        import re
        for c in cases:
            self.assertLessEqual(set(c), known, c["name"])
            for k in ("bash_matches", "not_bash_matches", "calls_match", "answer_matches"):
                for rx in c.get(k, []):
                    re.compile(rx)


if __name__ == "__main__":
    unittest.main()
