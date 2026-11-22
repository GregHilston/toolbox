"""herdr-adopt.py: which sessions get moved, and the resume command."""

from __future__ import annotations

import unittest

from _loader import load

adopt = load("herdr-adopt.py")


def session(**kw) -> dict:
    base = dict(pid=4242, sessionId="abc", cwd="/x", kind="interactive", entrypoint="cli",
                status="idle", idleFor=600, inHerdr=False, hasTranscript=True, cwdExists=True,
                argv="claude", name="Notes 9F!")
    return {**base, **kw}


class Classify(unittest.TestCase):
    def test_only_idle_loose_sessions_resume(self) -> None:
        self.assertEqual(adopt.classify(session(), 60)[0], "resume")
        for kw in (dict(inHerdr=True), dict(status="busy"), dict(status="waiting"),
                   dict(idleFor=5), dict(hasTranscript=False), dict(cwdExists=False)):
            self.assertEqual(adopt.classify(session(**kw), 60)[0], "skip", kw)

    def test_background_session_attaches(self) -> None:
        self.assertEqual(adopt.classify(session(kind="bg", jobId="j1", inHerdr=True), 60)[0], "attach")


class Resume(unittest.TestCase):
    def test_phone_session_keeps_model_mode_and_gets_remote_control(self) -> None:
        d = session(entrypoint="sdk-cli", argv="claude --print --model claude-sonnet-5-5 --permission-mode auto")
        self.assertEqual(adopt.resume_cmd(d), ["claude", "--resume", "abc", "--model", "claude-sonnet-5-5",
                                               "--permission-mode", "auto", "--remote-control"])

    def test_plain_terminal_session_has_no_remote_control(self) -> None:
        self.assertEqual(adopt.resume_cmd(session()), ["claude", "--resume", "abc"])

    def test_name_fits_herdr_rules(self) -> None:
        n = adopt.herdr_name(session(name="A very long Session name, with symbols!!"))
        self.assertRegex(n, r"^[a-z0-9_-]{1,32}$")


if __name__ == "__main__":
    unittest.main()
