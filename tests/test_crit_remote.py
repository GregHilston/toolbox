"""crit-remote.py finds live crit reviews from a host's session files."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from _loader import load

mod = load("crit-remote.py")


def session(pid: int, port: int, **kw) -> dict:
    return {"pid": pid, "port": port, "cwd": "/r", "branch": "main", "started_at": "2026-11-18T10:00:00Z", **kw}


class TestRemoteScript(unittest.TestCase):
    """Runs REMOTE as ssh would, with HOME as the host."""

    def run_remote(self, files: dict[str, dict | str]) -> str:
        with tempfile.TemporaryDirectory() as home:
            d = Path(home, ".crit", "sessions")
            d.mkdir(parents=True)
            for name, body in files.items():
                text = body if isinstance(body, str) else json.dumps(body, indent=2)
                Path(d, name).write_text(text)
            env = {**os.environ, "HOME": home}
            r = subprocess.run(["sh", "-s"], input=mod.REMOTE, capture_output=True, text=True, env=env)
            return r.stdout

    def test_keeps_live_drops_dead(self):
        live = os.getpid()
        out = self.run_remote({"a.json": session(live, 4001), "b.json": session(999999, 4002)})
        got = mod.parse_sessions(out)
        self.assertEqual([s["port"] for s in got], [4001])

    def test_no_sessions_dir_contents(self):
        self.assertEqual(mod.parse_sessions(self.run_remote({})), [])


class TestParse(unittest.TestCase):
    def test_newest_first(self):
        old = session(1, 10, started_at="2026-11-17T00:00:00Z")
        new = session(2, 20, started_at="2026-11-18T00:00:00Z")
        out = f"{json.dumps(old)}\n{json.dumps(new)}\n---ALIVE---\n1\n2\n"
        self.assertEqual([s["port"] for s in mod.parse_sessions(out)], [20, 10])

    def test_label(self):
        s = session(1, 10, cwd="/Users/g/Git/blurts-server", branch="MNTOR-1", args=["plan.md"])
        self.assertEqual(mod.label(s), "/Users/g/Git/blurts-server [MNTOR-1] plan.md")


class TestFreePort(unittest.TestCase):
    def test_falls_back_when_taken(self):
        import socket

        with socket.socket() as busy:
            busy.bind(("127.0.0.1", 0))
            busy.listen()
            taken = busy.getsockname()[1]
            self.assertNotEqual(mod.free_port(taken), taken)


if __name__ == "__main__":
    unittest.main()
