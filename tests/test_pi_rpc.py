"""pi-rpc's job is to make a running worker reachable, and then get out of the way.

The end-to-end behaviour (spawn, narrate, steer, settle) is only provable
against a real pi, so what is unit-tested here is the wiring that would fail
silently: where the control socket lives, which RPC command each op maps to,
how responses are correlated back to the client that asked, and that a
supervisor with no live process answers instead of hanging.
"""

from __future__ import annotations

import io
import json
import queue
import tempfile
import unittest
from pathlib import Path

from _loader import load

rpc = load("pi-rpc.py")


def make_supervisor(directory: Path, keep_alive: bool = False):
    narrator = rpc.narrate.Narrator(label="test", out=io.StringIO())
    return rpc.Supervisor(directory, [], narrator, None, keep_alive), narrator


class ControlPaths(unittest.TestCase):
    def test_the_socket_lives_outside_the_worker_directory(self):
        # macOS caps a Unix socket path at 104 bytes and a worktree path plus
        # `.pi/` gets close enough to matter, so the socket is hashed into the
        # temp directory and the worker holds only a pointer to it.
        with tempfile.TemporaryDirectory() as tmp:
            pointer, socket_path = rpc.control_paths(Path(tmp))
            self.assertEqual(pointer.parent.name, ".pi")
            self.assertNotIn(str(Path(tmp)), str(socket_path))
            self.assertLess(len(str(socket_path)), 104)

    def test_a_very_long_worker_path_still_yields_a_short_socket_path(self):
        deep = Path("/" + "/".join("worktree-with-a-long-name" for _ in range(12)))
        _, socket_path = rpc.control_paths(deep)
        self.assertLess(len(str(socket_path)), 104, "this is the whole reason for the hash")

    def test_the_socket_path_is_stable_and_distinct_per_worker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a").mkdir()
            (root / "b").mkdir()
            first = rpc.control_paths(root / "a")[1]
            self.assertEqual(first, rpc.control_paths(root / "a")[1], "stable across calls")
            self.assertNotEqual(first, rpc.control_paths(root / "b")[1], "one socket per worker")


class Dispatch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.supervisor, self.narrator = make_supervisor(Path(self.tmp.name))
        self.sent: list[dict] = []
        self.supervisor.command = lambda payload, wait=True: (  # type: ignore[method-assign]
            self.sent.append(payload) or {"success": True}
        )

    def test_steer_uses_pis_steer_command_not_a_plain_prompt(self):
        # A plain prompt is rejected mid-stream; steer is the one that lands
        # between the current tool calls and the next model call.
        self.supervisor.dispatch({"op": "steer", "message": "wrong file"})
        self.assertEqual(self.sent, [{"type": "steer", "message": "wrong file"}])

    def test_follow_up_maps_to_pis_snake_case_command(self):
        self.supervisor.dispatch({"op": "follow-up", "message": "then update the changelog"})
        self.assertEqual(self.sent[0]["type"], "follow_up")

    def test_state_and_abort_map_across(self):
        self.supervisor.dispatch({"op": "state"})
        self.supervisor.dispatch({"op": "abort"})
        self.assertEqual([c["type"] for c in self.sent], ["get_state", "abort"])

    def test_an_unknown_op_is_refused_rather_than_forwarded(self):
        result = self.supervisor.dispatch({"op": "rm -rf"})
        self.assertFalse(result["success"])
        self.assertEqual(self.sent, [], "nothing reaches pi")

    def test_a_message_op_with_no_message_is_refused(self):
        for message in (None, "", "   "):
            result = self.supervisor.dispatch({"op": "steer", "message": message})
            self.assertFalse(result["success"])
        self.assertEqual(self.sent, [])

    def test_stop_settles_the_run_without_talking_to_pi(self):
        result = self.supervisor.dispatch({"op": "stop"})
        self.assertTrue(result["success"])
        self.assertTrue(self.supervisor.stopping.is_set())
        self.assertTrue(self.supervisor.settled.is_set())
        self.assertEqual(self.sent, [])

    def test_an_orchestrator_intervention_is_narrated(self):
        # It must show up in the log beside the worker's own actions, or a diff
        # that changed direction mid-run has no explanation in it.
        self.supervisor.dispatch({"op": "steer", "message": "use src/foo.gd"})
        self.assertIn("steer from the orchestrator", self.narrator.out.getvalue())


class NoLiveProcess(unittest.TestCase):
    def test_commands_answer_immediately_rather_than_blocking(self):
        with tempfile.TemporaryDirectory() as tmp:
            supervisor, _ = make_supervisor(Path(tmp))
            result = supervisor.command({"type": "get_state"})
            self.assertFalse(result["success"])
            self.assertIn("not running", result["error"])

    def test_a_client_gets_a_useful_error_when_no_worker_is_listening(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = rpc.client_request(Path(tmp), {"op": "state"})
            self.assertFalse(result["success"])
            self.assertIn("no live worker", result["error"])


class ResponseRouting(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.supervisor, self.narrator = make_supervisor(Path(self.tmp.name))

    def test_a_response_reaches_the_client_that_asked_for_it(self):
        inbox: queue.Queue = queue.Queue(maxsize=1)
        self.supervisor.pending["sup-7"] = inbox
        self.supervisor.route_response({"type": "response", "id": "sup-7", "success": True})
        self.assertTrue(inbox.get_nowait()["success"])

    def test_an_uncorrelated_failure_is_narrated_rather_than_dropped(self):
        # A rejected steer with no waiter would otherwise vanish, and the
        # orchestrator would believe it had redirected a worker it had not.
        self.supervisor.route_response(
            {"type": "response", "command": "steer", "success": False, "error": "not streaming"}
        )
        self.assertIn("pi rejected steer", self.narrator.out.getvalue())

    def test_an_uncorrelated_success_is_not_noise(self):
        self.supervisor.route_response({"type": "response", "command": "abort", "success": True})
        self.assertEqual(self.narrator.out.getvalue(), "")

    def test_request_ids_are_unique(self):
        ids = {self.supervisor.next_id() for _ in range(50)}
        self.assertEqual(len(ids), 50, "a reused id would deliver a response to the wrong waiter")


class ArgumentHandling(unittest.TestCase):
    def setUp(self):
        self.captured: list = []
        original = rpc.cmd_run
        rpc.cmd_run = lambda args: (self.captured.append(args) or 0)  # type: ignore[assignment]
        self.addCleanup(lambda: setattr(rpc, "cmd_run", original))

    def run_main(self, *argv: str) -> list[str]:
        rpc.main(list(argv))
        return self.captured[-1].pi_args

    def test_the_double_dash_separator_is_stripped_before_pi_sees_it(self):
        # argparse.REMAINDER keeps the literal `--`. Passing it on would make pi
        # treat everything after as messages rather than options, silently
        # dropping --provider and running the worker on the wrong model.
        self.assertEqual(
            self.run_main("run", "--dir", ".", "--prompt", "x", "--", "--provider", "deepseek"),
            ["--provider", "deepseek"],
        )

    def test_pi_args_are_optional(self):
        self.assertEqual(self.run_main("run", "--dir", ".", "--prompt", "x"), [])


if __name__ == "__main__":
    unittest.main()
