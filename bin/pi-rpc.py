#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Run a pi worker in RPC mode so it can be steered while it is still working.

`pi -p` is a closed box: you hand it a prompt, it runs to completion, and the
only way to change its mind is to wait for it to finish and pay for a
`--continue`. Everything you learn while watching it — that it is editing the
wrong file, that it has misread the issue, that it is about to spend four
minutes on a dead end — is unusable until it is too late to matter.

`pi --mode rpc` is the same agent driven over a JSONL protocol on stdin/stdout,
which means a supervisor can hold the process open and inject a message
mid-flight. This is that supervisor. It:

  - spawns pi, sends the opening prompt, and narrates the event stream through
    `pi-narrate.py`, so a background run is readable rather than silent;
  - listens on a control socket, so `pi-rpc.py steer` reaches a *live* worker;
  - exits when pi reports `agent_settled`, which is the same lifecycle `-p` has,
    so a backgrounded run still ends and still notifies.

That last point is the design constraint. A daemon that outlives its work would
trade the completion notification for the steering, and the notification is what
keeps worker slots rotating. `--keep-alive` opts out for attended use.

Usage:
    # Spawn a worker (run this backgrounded; its stdout is the narration).
    pi-rpc.py run --dir worktrees/issue-16 --label issue-16 \\
      --prompt-file .claude/pi-prompts/issue-16.md \\
      --raw .claude/pi-logs/issue-16.jsonl --alerts .claude/pi-logs/alerts.log \\
      -- --provider deepseek --model deepseek-v4-pro --thinking high --approve

    # From another shell, while it is still running:
    pi-rpc.py state  --dir worktrees/issue-16
    pi-rpc.py steer  --dir worktrees/issue-16 "You are in the wrong file; see src/foo.gd"
    pi-rpc.py follow-up --dir worktrees/issue-16 "When done, update the CHANGELOG"
    pi-rpc.py abort  --dir worktrees/issue-16

`steer` lands after the current tool calls finish and before the next model
call, so it redirects the worker without corrupting a half-finished turn.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import queue
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

# The narration format lives in one place. `pi-narrate.py` is not importable by
# name (hyphens are not valid in module names, and the repo reserves snake_case
# for importable modules), so load it by path rather than duplicating it here.
_NARRATE_PATH = Path(__file__).resolve().parent / "pi-narrate.py"
_spec = importlib.util.spec_from_file_location("_pi_narrate", _NARRATE_PATH)
if _spec is None or _spec.loader is None:  # pragma: no cover - a broken checkout
    raise SystemExit(f"pi-rpc.py needs {_NARRATE_PATH}, which is missing")
narrate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(narrate)

# How long a client waits for pi to answer a command. Generous, because the
# reader thread may be busy draining a burst of streaming deltas first.
CLIENT_TIMEOUT = 30.0

# macOS caps a Unix socket path at 104 bytes, and a worktree path plus `.pi/`
# gets close enough to matter. So the socket lives in the temp directory under a
# hash of the worker directory, and the worker directory holds a pointer to it.
SOCKET_NAME_LENGTH = 16

# A steer is a sentence, not a payload. Bounding the read stops a client that
# opens a connection and never sends a newline from growing the buffer forever.
MAX_REQUEST_BYTES = 1 << 20


def read_line(connection: socket.socket, limit: int = MAX_REQUEST_BYTES) -> bytes:
    """One LF-terminated record off a socket, without unbounded buffering."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = connection.recv(65536)
        if not chunk:
            break
        newline = chunk.find(b"\n")
        if newline >= 0:
            chunks.append(chunk[:newline])
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > limit:
            raise ValueError(f"request exceeded {limit} bytes with no newline")
    return b"".join(chunks)


def read_request(connection: socket.socket) -> dict[str, Any]:
    payload = json.loads(read_line(connection) or b"{}")
    return payload if isinstance(payload, dict) else {}


def control_paths(directory: Path) -> tuple[Path, Path]:
    """(pointer file inside the worker, socket path in the temp directory)."""
    resolved = str(directory.resolve())
    digest = hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:SOCKET_NAME_LENGTH]
    socket_path = Path(tempfile.gettempdir()) / f"pi-rpc-{digest}.sock"
    return directory / ".pi" / "rpc.json", socket_path


class Supervisor:
    """Owns the pi subprocess, the event stream, and the control socket."""

    def __init__(
        self,
        directory: Path,
        pi_args: list[str],
        narrator: Any,
        raw: Any,
        keep_alive: bool,
    ) -> None:
        self.directory = directory
        self.pi_args = pi_args
        self.narrator = narrator
        self.raw = raw
        self.keep_alive = keep_alive
        self.process: subprocess.Popen[bytes] | None = None
        self.stdin_lock = threading.Lock()
        self.pending: dict[str, queue.Queue] = {}
        self.pending_lock = threading.Lock()
        self.settled = threading.Event()
        self.stopping = threading.Event()
        self.counter = 0
        self.server: socket.socket | None = None
        self.pointer, self.socket_path = control_paths(directory)
        # Joined before the output handles close, so the log keeps its tail.
        self.readers: list[threading.Thread] = []
        # Evidence that pi is alive and working, used instead of a bare timeout
        # to decide whether the opening prompt was actually refused.
        self.saw_event = threading.Event()
        self.owns_socket = False

    # ---- talking to pi -------------------------------------------------

    def next_id(self) -> str:
        with self.pending_lock:
            self.counter += 1
            return f"sup-{self.counter}"

    def command(self, payload: dict[str, Any], wait: bool = True) -> dict[str, Any]:
        """Send one RPC command; optionally block for its correlated response."""
        process = self.process
        if process is None or process.stdin is None or process.poll() is not None:
            return {"success": False, "error": "pi is not running"}
        request_id = self.next_id()
        payload = {**payload, "id": request_id}
        inbox: queue.Queue = queue.Queue(maxsize=1)
        if wait:
            with self.pending_lock:
                self.pending[request_id] = inbox
        line = (json.dumps(payload) + "\n").encode("utf-8")
        try:
            with self.stdin_lock:
                process.stdin.write(line)
                process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            with self.pending_lock:
                self.pending.pop(request_id, None)
            return {"success": False, "error": f"could not reach pi: {exc}"}
        if not wait:
            return {"success": True}
        try:
            return inbox.get(timeout=CLIENT_TIMEOUT)
        except queue.Empty:
            return {"success": False, "error": f"pi did not answer within {CLIENT_TIMEOUT:g}s"}
        finally:
            with self.pending_lock:
                self.pending.pop(request_id, None)

    # ---- reading from pi -----------------------------------------------

    def read_events(self) -> None:
        process = self.process
        assert process is not None and process.stdout is not None
        for record in narrate.records(process.stdout):
            if self.raw is not None:
                self.raw.write(record + b"\n")
                self.raw.flush()
            text = record.decode("utf-8", errors="replace").strip()
            if not text:
                continue
            try:
                event = json.loads(text)
            except ValueError:
                self.narrator.feed(text)
                continue
            if isinstance(event, dict) and event.get("type") == "response":
                self.route_response(event)
                continue
            self.saw_event.set()
            self.narrator.feed(text)
            if isinstance(event, dict) and event.get("type") == "agent_settled":
                self.settled.set()
        # pi's stdout closed: it exited, cleanly or otherwise. Fail every
        # waiting client now rather than letting each burn the full timeout —
        # a pi that dies during startup would otherwise make the opening prompt
        # take CLIENT_TIMEOUT seconds to report a failure that is already known.
        with self.pending_lock:
            waiting = list(self.pending.values())
            self.pending.clear()
        for inbox in waiting:
            try:
                inbox.put_nowait({"success": False, "error": "pi exited"})
            except queue.Full:
                pass
        self.settled.set()
        self.stopping.set()

    def route_response(self, event: dict[str, Any]) -> None:
        request_id = event.get("id")
        with self.pending_lock:
            inbox = self.pending.get(request_id) if isinstance(request_id, str) else None
        if inbox is None:
            # An uncorrelated failure is still worth seeing — a rejected steer
            # would otherwise vanish silently.
            if not event.get("success", True):
                self.narrator.emit("!", f"pi rejected {event.get('command')}: {event.get('error')}")
            return
        try:
            inbox.put_nowait(event)
        except queue.Full:  # pragma: no cover - the queue is drained by one waiter
            pass

    def read_stderr(self) -> None:
        """pi's stderr is kept off the event stream so responses always parse."""
        process = self.process
        assert process is not None and process.stderr is not None
        for line in process.stderr:
            text = line.decode("utf-8", errors="replace").strip()
            if text:
                self.narrator.emit("!", text)

    # ---- the control socket --------------------------------------------

    def socket_is_live(self) -> bool:
        """Is another supervisor already serving this directory?"""
        if not self.socket_path.exists():
            return False
        probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        probe.settimeout(2)
        with probe:
            try:
                probe.connect(str(self.socket_path))
            except OSError:
                return False  # Stale file from a supervisor that died.
        return True

    def serve(self) -> None:
        # Unguarded, a failed bind or unlink would kill this daemon thread with
        # a bare traceback and leave the run going with no control socket and
        # nothing saying so. Losing steering must be reported, not silent.
        try:
            self.bind_and_serve()
        except Exception as exc:  # noqa: BLE001 - the run continues without steering
            self.narrator.emit("!", f"no control socket; steering is unavailable: {exc}")

    def bind_and_serve(self) -> None:
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        if self.socket_is_live():
            # Unlinking here would take over a live supervisor's socket, and
            # then *its* exit would delete ours — leaving a working worker
            # permanently unreachable. Refuse instead.
            raise RuntimeError(
                f"another supervisor is already serving {self.directory}; "
                "stop it before starting a second one"
            )
        # Only now is the file provably stale.
        self.socket_path.unlink(missing_ok=True)
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(self.socket_path))
        # The socket accepts `prompt` and `steer` for an agent running with
        # --approve. On macOS $TMPDIR is already per-user and 0700, but on Linux
        # this lands in a shared /tmp, where anyone could otherwise drive it.
        os.chmod(self.socket_path, 0o600)
        server.listen(8)
        server.settimeout(0.5)
        self.server = server
        self.owns_socket = True

        self.pointer.parent.mkdir(parents=True, exist_ok=True)
        self.pointer.write_text(
            json.dumps(
                {
                    "socket": str(self.socket_path),
                    "pid": os.getpid(),
                    "piPid": self.process.pid if self.process else None,
                    "dir": str(self.directory.resolve()),
                    "startedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        while not self.stopping.is_set():
            try:
                connection, _ = server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self.handle_client, args=(connection,), daemon=True).start()

    def handle_client(self, connection: socket.socket) -> None:
        with connection:
            try:
                connection.settimeout(CLIENT_TIMEOUT + 5)
                response = self.dispatch(read_request(connection))
            except (ValueError, OSError) as exc:
                response = {"success": False, "error": str(exc)}
            try:
                connection.sendall((json.dumps(response) + "\n").encode("utf-8"))
            except OSError:
                pass

    def dispatch(self, request: dict[str, Any]) -> dict[str, Any]:
        op = request.get("op")
        message = request.get("message")
        if op == "state":
            return self.command({"type": "get_state"})
        if op == "abort":
            self.narrator.emit("⚠", "abort requested by the orchestrator")
            return self.command({"type": "abort"})
        if op == "stop":
            self.narrator.emit("⚠", "stop requested by the orchestrator")
            self.stopping.set()
            self.settled.set()
            return {"success": True}
        if op in ("steer", "follow-up", "prompt"):
            if not isinstance(message, str) or not message.strip():
                return {"success": False, "error": f"{op} needs a non-empty message"}
            self.narrator.emit("⚠", f"{op} from the orchestrator: {narrate.flatten(message)}")
            kind = {"steer": "steer", "follow-up": "follow_up", "prompt": "prompt"}[op]
            return self.command({"type": kind, "message": message})
        return {"success": False, "error": f"unknown op: {op!r}"}

    # ---- lifecycle ------------------------------------------------------

    def refused(self, answer: dict[str, Any]) -> bool:
        """Did pi actually reject the prompt, or did we merely not hear back?

        Only a correlated `success: false` — or a dead process — is a refusal.
        Treating a bare timeout as one killed workers that were visibly working:
        an ack that arrives late, or not at all, is not evidence of rejection,
        and the events already streaming in are evidence against it.
        """
        if answer.get("error") == "pi is not running":
            return True
        if self.settled.is_set() or self.saw_event.is_set():
            return False
        process = self.process
        if process is not None and process.poll() is None:
            # Alive and silent. Nothing has gone wrong that we can prove; let it
            # run and let the settle-or-exit loop below decide.
            self.narrator.emit(
                "⚠",
                f"pi has not acknowledged the opening prompt after {CLIENT_TIMEOUT:g}s; "
                "carrying on because the process is still alive",
            )
            return False
        return True

    def start(self, prompt: str) -> int:
        # PI_RPC_BIN exists so the supervisor's own lifecycle can be tested
        # against a stand-in that speaks the protocol. It also lets a run pin a
        # specific pi build without touching $PATH.
        self.process = subprocess.Popen(
            [os.environ.get("PI_RPC_BIN", "pi"), "--mode", "rpc", *self.pi_args],
            cwd=str(self.directory),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        reader = threading.Thread(target=self.read_events, name="pi-events", daemon=True)
        stderr_reader = threading.Thread(target=self.read_stderr, name="pi-stderr", daemon=True)
        self.readers = [reader, stderr_reader]
        reader.start()
        stderr_reader.start()
        threading.Thread(target=self.serve, name="pi-control", daemon=True).start()

        opened = self.command({"type": "prompt", "message": prompt})
        if not opened.get("success", False) and self.refused(opened):
            self.narrator.emit("!", f"pi refused the opening prompt: {opened.get('error')}")
            self.shutdown()
            return 1

        try:
            while not self.settled.wait(timeout=0.5):
                if self.process.poll() is not None:
                    break
            if self.keep_alive and self.process.poll() is None:
                self.narrator.emit("·", "settled; holding the session open (--keep-alive)")
                while not self.stopping.wait(timeout=0.5):
                    if self.process.poll() is not None:
                        break
        except KeyboardInterrupt:
            self.narrator.emit("⚠", "interrupted; shutting the worker down")
        return self.shutdown()

    def close_stdin(self, process: subprocess.Popen[bytes]) -> None:
        """Close pi's stdin without letting a stuck writer wedge the shutdown.

        `command()` holds `stdin_lock` across the write, and that write blocks
        once pi stops draining the pipe. Taking the lock unconditionally here
        meant a wedged pi deadlocked the supervisor *before* the terminate/kill
        escalation below could run — leaving a process only SIGKILL could clear.
        """
        if process.stdin is None:
            return
        acquired = self.stdin_lock.acquire(timeout=5)
        if not acquired:
            self.narrator.emit("!", "a write to pi is stuck; skipping the clean stdin close")
            return
        try:
            process.stdin.close()
        except OSError:
            pass
        finally:
            self.stdin_lock.release()

    def shutdown(self) -> int:
        self.stopping.set()
        process = self.process
        code = 0
        if process is not None and process.poll() is None:
            self.close_stdin(process)
            try:
                code = process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                self.narrator.emit("!", "pi did not exit after its stdin closed; terminating")
                process.terminate()
                try:
                    code = process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    code = process.wait()
        elif process is not None:
            code = process.returncode or 0

        # Drain before the caller closes the log handles. These threads are
        # daemons writing into `self.raw` and the narrator's streams; returning
        # while they are mid-flush truncated the JSONL and the alerts file, and
        # raised "I/O operation on closed file" out of a thread nobody watches.
        for reader in self.readers:
            reader.join(timeout=10)
            if reader.is_alive():
                self.narrator.emit("!", f"{reader.name} did not finish; its output may be short")

        # The readers are done with them now. Left open, each worker leaks two
        # descriptors, which matters when an orchestrator runs eight at a time.
        if process is not None:
            for pipe in (process.stdout, process.stderr, process.stdin):
                try:
                    if pipe is not None:
                        pipe.close()
                except OSError:
                    pass

        # Exactly one closing line per worker, whether it settled or died. The
        # alerts monitor in Step P2-bis is watching for it.
        self.narrator.finish()

        if self.server is not None:
            try:
                self.server.close()
            except OSError:
                pass
        # Only clean up what we actually own. A second supervisor is refused at
        # bind time, but if one ever does exist, deleting its socket here would
        # leave a live worker permanently unreachable.
        if self.owns_socket:
            self.socket_path.unlink(missing_ok=True)
            self.pointer.unlink(missing_ok=True)
        return code


def client_request(directory: Path, request: dict[str, Any]) -> dict[str, Any]:
    pointer, fallback = control_paths(directory)
    socket_path = fallback
    try:
        info = json.loads(pointer.read_text(encoding="utf-8"))
        if isinstance(info, dict) and isinstance(info.get("socket"), str):
            socket_path = Path(info["socket"])
    except (OSError, ValueError):
        # No pointer file: either the worker is not running, or it predates
        # this script. Try the derived path before giving up.
        pass
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    connection.settimeout(CLIENT_TIMEOUT + 10)
    with connection:
        try:
            connection.connect(str(socket_path))
        except OSError as exc:
            return {
                "success": False,
                "error": (
                    f"no live worker at {directory} ({exc}). "
                    "Is it running under `pi-rpc.py run`?"
                ),
            }
        # Send and receive are guarded too. A wedged supervisor made this raise
        # TimeoutError out of recv, so a caller expecting the documented JSON
        # result got a traceback on stderr instead.
        try:
            connection.sendall((json.dumps(request) + "\n").encode("utf-8"))
            payload = read_line(connection)
        except OSError as exc:
            return {
                "success": False,
                "error": f"the worker at {directory} accepted the connection but did not reply: {exc}",
            }
    try:
        return json.loads(payload or b"{}")
    except ValueError:
        return {"success": False, "error": "the supervisor sent a malformed reply"}


def cmd_run(args: argparse.Namespace) -> int:
    directory = Path(os.path.expanduser(args.dir)).resolve()
    if not directory.is_dir():
        print(f"pi-rpc: {directory} is not a directory", file=sys.stderr)
        return 2
    if args.prompt_file:
        try:
            prompt = Path(os.path.expanduser(args.prompt_file)).read_text(encoding="utf-8")
        except OSError as exc:
            # A bad --dir gets a clean message two lines up; this should too.
            print(f"pi-rpc: cannot read {args.prompt_file}: {exc}", file=sys.stderr)
            return 2
    elif args.prompt:
        prompt = args.prompt
    else:
        prompt = sys.stdin.read()
    if not prompt.strip():
        print("pi-rpc: refusing to start a worker with an empty prompt", file=sys.stderr)
        return 2

    raw = None
    alerts = None
    if args.raw:
        os.makedirs(os.path.dirname(os.path.abspath(args.raw)), exist_ok=True)
        # Append, not truncate: the doc's per-issue naming means a re-run or a
        # feedback pass points at the same path, and losing the first run's log
        # is exactly the outcome this tool exists to prevent.
        raw = open(args.raw, "ab")
    if args.alerts:
        os.makedirs(os.path.dirname(os.path.abspath(args.alerts)), exist_ok=True)
        alerts = open(args.alerts, "a", encoding="utf-8")

    narrator = narrate.Narrator(
        label=args.label or directory.name,
        out=sys.stdout,
        alerts=alerts,
        width=args.width,
        show_thinking=args.thinking,
    )
    supervisor = Supervisor(directory, args.pi_args, narrator, raw, args.keep_alive)

    def on_signal(signum: int, _frame: Any) -> None:
        narrator.emit("⚠", f"received signal {signum}; shutting the worker down")
        supervisor.stopping.set()
        supervisor.settled.set()

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)

    try:
        return supervisor.start(prompt)
    finally:
        for handle in (raw, alerts):
            if handle is not None:
                try:
                    handle.close()
                except OSError:
                    pass


def cmd_client(args: argparse.Namespace, op: str) -> int:
    directory = Path(os.path.expanduser(args.dir))
    request: dict[str, Any] = {"op": op}
    if op in ("steer", "follow-up", "prompt"):
        request["message"] = args.message
    response = client_request(directory, request)
    print(json.dumps(response, indent=2))
    return 0 if response.get("success") else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Supervise a steerable pi worker.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Spawn a worker and narrate it until it settles.")
    run.add_argument("--dir", required=True, help="Worker directory (the worktree).")
    run.add_argument("--label", help="Narration prefix. Default: the directory name.")
    run.add_argument("--prompt-file", help="File holding the opening prompt.")
    run.add_argument("--prompt", help="Opening prompt inline. Prefer --prompt-file.")
    run.add_argument("--raw", help="Write the untouched JSONL event stream here.")
    run.add_argument("--alerts", help="Append alert-worthy lines to this shared file.")
    run.add_argument("--width", type=int, default=200, help="Truncate narration to N chars.")
    run.add_argument("--thinking", action="store_true", help="Also narrate reasoning.")
    run.add_argument(
        "--keep-alive",
        action="store_true",
        help="Stay up after the agent settles, for attended supervision.",
    )
    run.add_argument(
        "pi_args",
        nargs=argparse.REMAINDER,
        help="Everything after `--` is passed to pi verbatim.",
    )

    for name, helptext in (
        ("state", "Ask a live worker what it is doing."),
        ("abort", "Abort a live worker's current operation."),
        ("stop", "Shut a live worker down."),
    ):
        sub = subparsers.add_parser(name, help=helptext)
        sub.add_argument("--dir", required=True, help="Worker directory.")

    for name, helptext in (
        ("steer", "Redirect a live worker before its next model call."),
        ("follow-up", "Queue work for a live worker to do once it finishes."),
        ("prompt", "Send a plain prompt (fails if the worker is mid-stream)."),
    ):
        sub = subparsers.add_parser(name, help=helptext)
        sub.add_argument("--dir", required=True, help="Worker directory.")
        sub.add_argument("message", help="What to tell it.")

    args = parser.parse_args(argv)
    if args.command == "run":
        # argparse.REMAINDER keeps the `--` separator; pi should not see it.
        if args.pi_args and args.pi_args[0] == "--":
            args.pi_args = args.pi_args[1:]
        return cmd_run(args)
    return cmd_client(args, args.command)


if __name__ == "__main__":
    sys.exit(main())
