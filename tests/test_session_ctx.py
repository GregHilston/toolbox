"""session-ctx.py reads the last chunk of the last assistant message."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load

ctx = load("session-ctx.py")


def assistant(msg_id: str, inp: int, read: int, create: int, **extra) -> str:
    usage = {"input_tokens": inp, "cache_read_input_tokens": read, "cache_creation_input_tokens": create}
    return json.dumps({"type": "assistant", "message": {"id": msg_id, "usage": usage}, **extra})


class SessionCtx(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.fixture = self.dir / "t.jsonl"
        self.fixture.write_text("\n".join([
            json.dumps({"type": "user", "message": {"content": "hi"}}),
            assistant("m1", 1, 1000, 500),
            assistant("m2", 3, 40000, 2000),
            assistant("m2", 3, 90000, 10000),  # streamed duplicate: the last chunk wins
            assistant("side", 1, 900000, 0, isSidechain=True),
            "not json",
        ]) + "\n")

    def run_main(self, *args: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = ctx.main([*args])
        return code, out.getvalue()

    def test_size_is_the_last_chunk_of_the_last_message(self) -> None:
        self.assertEqual(ctx.context_tokens(self.fixture), 100003)

    def test_exit_code_follows_the_cap(self) -> None:
        self.assertEqual(self.run_main(str(self.fixture)), (0, "100003 tokens (cap 150000)\n"))
        self.assertEqual(self.run_main(str(self.fixture), "--cap", "100000"), (1, "100003 tokens (cap 100000) OVER\n"))

    def test_env_var_sets_the_cap(self) -> None:
        with mock.patch.dict("os.environ", {"SESSION_CTX_CAP": "300000"}):
            self.assertEqual(ctx.cap(), 300000)
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(ctx.cap(), 150000)

    def test_newest_transcript_for_the_cwd(self) -> None:
        folder = self.dir / "projects" / "-work-proj"
        folder.mkdir(parents=True)
        (folder / "old.jsonl").write_text("")
        (folder / "new.jsonl").write_text("")
        (folder / "old.jsonl").touch()
        (folder / "new.jsonl").touch()
        with mock.patch.object(ctx, "PROJECTS", self.dir / "projects"):
            self.assertEqual(ctx.newest_transcript(Path("/work/proj")), folder / "new.jsonl")
            self.assertIsNone(ctx.newest_transcript(Path("/elsewhere")))

    def test_short(self) -> None:
        self.assertEqual(ctx.short(253000), "253k")


if __name__ == "__main__":
    unittest.main()
