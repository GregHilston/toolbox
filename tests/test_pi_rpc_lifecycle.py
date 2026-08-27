"""End-to-end tests for the parts of pi-rpc.py that own threads and sockets.

Everything severe found in review lived here — a shutdown that deadlocked on a
wedged write, a log tail lost to daemon threads, a healthy worker killed for a
slow ack, a client that raised instead of answering. None of it is reachable
through the pure functions; all of it is reachable against `fake_pi.py`, which
speaks the protocol badly on request.

These spawn processes and bind sockets, so they are far slower than the unit
tests — the `Wedged` cases deliberately drive the shutdown escalation and take
tens of seconds each. That is the price of covering the only code paths where
the real defects were.
"""

from __future__ import annotations

import io
import json
import os
import stat
import threading
import time
import unittest
from pathlib import Path

from _loader import load

rpc = load("pi-rpc.py")

FAKE_PI = Path(__file__).resolve().parent / "fake_pi.py"


class Harness(unittest.TestCase):
    """A supervisor running against fake_pi.py in a scratch worker directory."""

    def setUp(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.out = io.StringIO()
        self.alerts = io.StringIO()
        self.raw_path = self.root / "raw.jsonl"

        self.env_backup = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self.env_backup)))
        # The supervisor invokes `<bin> --mode rpc <pi_args...>`, so the stand-in
        # has to *be* the executable; fake_pi.py ignores the flags it is handed.
        os.environ["PI_RPC_BIN"] = str(FAKE_PI)
        os.environ["FAKE_PI_TURNS"] = "2"
        for name in ("FAKE_PI_ACK_PROMPT", "FAKE_PI_SETTLE", "FAKE_PI_STDERR_LINES",
                     "FAKE_PI_IGNORE_STDIN", "FAKE_PI_HANG"):
            os.environ.pop(name, None)

    def make(self, keep_alive=False, raw=None):
        narrator = rpc.narrate.Narrator(label="w1", out=self.out, alerts=self.alerts)
        return rpc.Supervisor(self.root, [], narrator, raw, keep_alive), narrator

    def run_supervisor(self, supervisor, prompt="do the thing"):
        code = supervisor.start(prompt)
        return code

    def narration(self) -> str:
        return self.out.getvalue()


class HappyPath(Harness):
    def test_a_run_narrates_settles_and_cleans_up_after_itself(self):
        supervisor, _ = self.make()
        code = self.run_supervisor(supervisor)
        self.assertEqual(code, 0)
        narration = self.narration()
        self.assertIn("▸ bash echo 1", narration)
        self.assertIn("■ done", narration, "the completion line the alerts monitor waits for")
        self.assertIn("■ done", self.alerts.getvalue())
        self.assertFalse(supervisor.socket_path.exists(), "no stale socket")
        self.assertFalse(supervisor.pointer.exists(), "no stale rpc.json")

    def test_the_raw_log_keeps_its_tail(self):
        # Daemon reader threads writing into a handle the main thread closed
        # truncated this, and raised "I/O operation on closed file" out of a
        # thread nobody watches.
        os.environ["FAKE_PI_TURNS"] = "40"
        with open(self.raw_path, "wb") as raw:
            supervisor, _ = self.make(raw=raw)
            self.run_supervisor(supervisor)
        records = self.raw_path.read_bytes().splitlines()
        kinds = [json.loads(line)["type"] for line in records if line.strip()]
        self.assertIn("agent_settled", kinds, "the last event must reach the log")
        self.assertEqual(kinds.count("turn_start"), 40, "and so must every event before it")

    def test_stderr_reaches_the_narration_rather_than_being_lost(self):
        os.environ["FAKE_PI_STDERR_LINES"] = "50"
        supervisor, _ = self.make()
        self.run_supervisor(supervisor)
        self.assertEqual(
            self.narration().count("! fake-pi stderr line"), 50, "every line, not a truncated tail"
        )


class ControlSocket(Harness):
    def start_in_background(self, supervisor):
        thread = threading.Thread(target=supervisor.start, args=("go",), daemon=True)
        thread.start()
        deadline = time.time() + 10
        while time.time() < deadline and not supervisor.pointer.exists():
            time.sleep(0.02)
        return thread

    def test_a_client_can_steer_a_live_worker(self):
        os.environ["FAKE_PI_TURNS"] = "40"
        supervisor, _ = self.make()
        thread = self.start_in_background(supervisor)
        try:
            answer = rpc.client_request(self.root, {"op": "steer", "message": "use src/foo.gd"})
            self.assertTrue(answer.get("success"), answer)
            state = rpc.client_request(self.root, {"op": "state"})
            self.assertIn("use src/foo.gd", state["data"]["steers"], "it reached the agent")
        finally:
            rpc.client_request(self.root, {"op": "abort"})
            thread.join(timeout=30)
        self.assertIn("steer from the orchestrator", self.narration())

    def test_the_socket_is_not_readable_by_other_users(self):
        # It accepts `prompt` and `steer` for an agent running with --approve.
        # On a Linux host this lands in a shared /tmp.
        os.environ["FAKE_PI_TURNS"] = "40"
        supervisor, _ = self.make()
        thread = self.start_in_background(supervisor)
        try:
            mode = stat.S_IMODE(supervisor.socket_path.stat().st_mode)
            self.assertEqual(mode, 0o600, f"socket mode was {oct(mode)}")
        finally:
            rpc.client_request(self.root, {"op": "abort"})
            thread.join(timeout=30)

    def test_a_second_supervisor_is_refused_rather_than_stealing_the_socket(self):
        # Taking over would be bad enough; the real damage was that the first
        # supervisor's exit then deleted the second's socket and rpc.json,
        # leaving a live worker permanently unreachable.
        os.environ["FAKE_PI_TURNS"] = "40"
        first, _ = self.make()
        thread = self.start_in_background(first)
        try:
            second, second_narrator = self.make()
            second.process = first.process  # so bind is the only thing under test
            second.serve()
            self.assertIn("another supervisor is already serving", self.narration())
            self.assertFalse(second.owns_socket)
            # The first supervisor is untouched and still reachable.
            self.assertTrue(rpc.client_request(self.root, {"op": "state"}).get("success"))
        finally:
            rpc.client_request(self.root, {"op": "abort"})
            thread.join(timeout=30)

    def test_a_stale_socket_file_does_not_block_a_new_run(self):
        supervisor, _ = self.make()
        supervisor.socket_path.parent.mkdir(parents=True, exist_ok=True)
        supervisor.socket_path.write_bytes(b"")  # a corpse from a killed supervisor
        self.assertEqual(self.run_supervisor(supervisor), 0)
        self.assertIn("■ done", self.narration())


class Wedged(Harness):
    def setUp(self):
        super().setUp()
        # These tests are about decisions, not about waiting for them. The
        # real 30s is what made the old failures expensive, not what caused
        # them.
        self.addCleanup(lambda: setattr(rpc, "CLIENT_TIMEOUT", 30.0))
        rpc.CLIENT_TIMEOUT = 1.0

    def test_shutdown_does_not_deadlock_on_a_pi_that_stopped_reading_stdin(self):
        # A client write blocks in the pipe holding stdin_lock; shutdown used to
        # take the same lock and wait forever, so the terminate/kill escalation
        # never ran and only SIGKILL cleared it.
        os.environ["FAKE_PI_IGNORE_STDIN"] = "1"
        os.environ["FAKE_PI_HANG"] = "1"
        os.environ["FAKE_PI_TURNS"] = "1"
        supervisor, _ = self.make()

        thread = threading.Thread(target=supervisor.start, args=("go",), daemon=True)
        thread.start()
        deadline = time.time() + 20
        while time.time() < deadline and not supervisor.pointer.exists():
            time.sleep(0.05)
        self.assertTrue(supervisor.pointer.exists(), "the control socket never came up")

        # Wedge the write path the way the real thing does: a steer larger than
        # the pipe buffer, into a pi that is not draining it. The supervisor's
        # own `command()` then blocks inside `write` while holding stdin_lock.
        # (Faking this by taking the lock from the test races the opening
        # prompt, and wedges `command()` instead of the shutdown.)
        big = "x" * (512 * 1024)
        threading.Thread(
            target=rpc.client_request,
            args=(self.root, {"op": "steer", "message": big}),
            daemon=True,
        ).start()

        deadline = time.time() + 20
        while time.time() < deadline and not supervisor.stdin_lock.locked():
            time.sleep(0.05)
        self.assertTrue(supervisor.stdin_lock.locked(), "the write never wedged; test is not valid")

        started = time.time()
        # 5s bounded lock acquire + 20s wait + 10s terminate is the design worst
        # case. Before the fix this never finished at all.
        thread.join(timeout=90)
        self.assertFalse(thread.is_alive(), "the supervisor never exited")
        self.assertLess(time.time() - started, 60, "it exited, but not by the design path")
        self.assertIn("stuck", self.narration(), "and it says why, rather than hanging silently")

    def test_a_slow_ack_does_not_kill_a_working_worker(self):
        # Treating a bare timeout as a refusal killed workers that were visibly
        # working, after burning the full client timeout doing nothing.
        os.environ["FAKE_PI_ACK_PROMPT"] = "0"
        os.environ["FAKE_PI_TURNS"] = "3"
        supervisor, _ = self.make()

        code = self.run_supervisor(supervisor)
        narration = self.narration()
        self.assertNotIn("refused the opening prompt", narration)
        self.assertIn("▸ bash echo 3", narration, "it ran to completion")
        self.assertIn("■ done", narration)
        self.assertEqual(code, 0)

    def test_a_worker_that_dies_without_settling_still_reports_completion(self):
        # The alerts monitor counts on exactly one closing line per worker. A
        # crash mid-run must produce it too, or a dead worker is silent on the
        # one channel that was supposed to interrupt someone.
        os.environ["FAKE_PI_SETTLE"] = "0"
        supervisor, _ = self.make()
        code = self.run_supervisor(supervisor)
        self.assertEqual(code, 1, "and the failing exit status is not swallowed")
        self.assertIn("■ done", self.narration())
        self.assertIn("■ done", self.alerts.getvalue())


class ClientErrors(unittest.TestCase):
    def test_a_client_answers_with_json_when_the_supervisor_never_replies(self):
        # recv used to raise TimeoutError straight out of client_request, so a
        # caller expecting the documented JSON result got a traceback instead.
        import socket
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            pointer, socket_path = rpc.control_paths(directory)
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            socket_path.unlink(missing_ok=True)
            server.bind(str(socket_path))
            server.listen(1)
            self.addCleanup(lambda: (server.close(), socket_path.unlink(missing_ok=True)))

            rpc.CLIENT_TIMEOUT = 0.2
            self.addCleanup(lambda: setattr(rpc, "CLIENT_TIMEOUT", 30.0))
            answer = rpc.client_request(directory, {"op": "state"})
            self.assertFalse(answer["success"])
            self.assertIn("did not reply", answer["error"])

    def test_read_line_refuses_an_endless_request(self):
        import socket

        left, right = socket.socketpair()
        self.addCleanup(left.close)
        self.addCleanup(right.close)

        def flood():
            try:
                for _ in range(40):
                    right.sendall(b"x" * 65536)
            except OSError:
                pass

        threading.Thread(target=flood, daemon=True).start()
        with self.assertRaises(ValueError):
            rpc.read_line(left, limit=1 << 16)


if __name__ == "__main__":
    unittest.main()
