"""fetch-thread.py reruns a blocked Reddit fetch on another host over ssh."""

from __future__ import annotations

import subprocess
import sys
import unittest
from unittest import mock

from _loader import BIN, load

sys.path.insert(0, str(BIN))
ft = load("fetch-thread.py")


class Blocked(unittest.TestCase):
    def test_refusals_relay(self) -> None:
        for msg in ("HTTP 403 on /svc/x: Reddit blocked the request", "HTTP 429 on /r/x.rss: rate-limited"):
            self.assertTrue(ft.blocked(RuntimeError(msg)), f"{msg!r} should relay")

    def test_other_errors_do_not(self) -> None:
        self.assertFalse(ft.blocked(ValueError("no post id in URL")), "a bad URL should not relay")


class Relay(unittest.TestCase):
    def run_relay(self, results: dict[str, subprocess.CompletedProcess]) -> tuple[str | None, list[str]]:
        tried: list[str] = []

        def fake_run(cmd, **_kw):
            host = cmd[5]
            tried.append(host)
            return results[host]

        env = {"FETCH_THREAD_RELAYS": "moria dungeon fob"}
        with mock.patch.object(ft.subprocess, "run", fake_run), mock.patch.dict(ft.os.environ, env), \
                mock.patch.object(ft.socket, "gethostname", return_value="moria.local"):
            return ft.relay(["https://reddit.com/r/x/comments/abc"]), tried

    def test_skips_this_host_and_returns_first_answer(self) -> None:
        out, tried = self.run_relay({
            "dungeon": subprocess.CompletedProcess([], 1, b"", b"Error: HTTP 403"),
            "fob": subprocess.CompletedProcess([], 0, b"# thread\n", b""),
        })
        self.assertEqual(tried, ["dungeon", "fob"], f"tried {tried}, want dungeon then fob, never moria")
        self.assertEqual(out, "# thread\n", f"got {out!r}, want fob's answer")

    def test_none_when_every_relay_fails(self) -> None:
        fail = subprocess.CompletedProcess([], 1, b"", b"Error: HTTP 429")
        out, _ = self.run_relay({"dungeon": fail, "fob": fail})
        self.assertIsNone(out, f"got {out!r}, want None")


if __name__ == "__main__":
    unittest.main()
