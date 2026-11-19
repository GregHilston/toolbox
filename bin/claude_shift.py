"""Shared state for Claude Code orchestrator shifts: shift-arm, orchestrator-roll, shift-drain.py.

A shift is one context window of an armed orchestrator. State is one JSON file
per Herdr pane, keyed on HERDR_PANE_ID: Claude Code's session_id changes on
/clear, but the pane and the env Herdr gave the process don't. Herdr never
reuses a pane id, and a pane moved to another workspace still resolves its old
id for the process that inherited it. Every read-modify-write holds a flock,
because the Stop hook, the roll worker and shift-arm all write the file.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import subprocess
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

STATE_DIR = Path(os.environ.get("CLAUDE_SHIFT_DIR") or Path.home() / ".cache/claude-shift")
PUSHOVER = os.environ.get("PUSHOVER_BIN") or str(Path(__file__).resolve().parent / "pushover.py")
USAGE_KEYS = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
SCHEMA = {
    "pane": str, "threshold": int, "prompt": str, "max_rolls": int, "rolls": int, "repo": str,
    "announced": (str, type(None)), "tokens": (int, type(None)), "stops": int, "busy": int,
    "roll_id": (str, type(None)), "roll_stops": int, "worker_pid": (int, type(None)),
}  # fmt: skip
RUNTIME = {"announced": None, "tokens": None, "stops": 0, "busy": 0, "roll_id": None, "roll_stops": 0, "worker_pid": None}


def hook_problem() -> str | None:
    """What is missing for the Stop hook to run, or None."""
    config = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    hook = config / "hooks/shift-drain.py"
    if not hook.is_file() or not os.access(hook, os.X_OK):
        return f"{hook} is missing or not executable"
    try:
        stops = json.loads((config / "settings.json").read_text())["hooks"]["Stop"]
        commands = [h.get("command", "") for group in stops for h in group["hooks"]]
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        commands = []
    if not any("shift-drain.py" in c for c in commands):
        return f"no hooks.Stop command in {config / 'settings.json'} names shift-drain.py"
    return None


class Invalid(Exception):
    pass


def pane() -> str | None:
    # the desktop app's terminals set HC_*, not HERDR_*
    if os.environ.get("HERDR_PANE_ID"):
        return os.environ["HERDR_PANE_ID"]
    terminal = os.environ.get("HC_TERMINAL_ID")
    return f"hc:{terminal}" if terminal else None


def state_path(pane_id: str) -> Path:
    return STATE_DIR / (hashlib.sha256(pane_id.encode()).hexdigest()[:16] + ".json")


def log_path(pane_id: str) -> Path:
    return state_path(pane_id).with_suffix(".log")


def short(text: object, limit: int = 200) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def log(pane_id: str, message: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(log_path(pane_id), "a") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {message}\n")


@contextmanager
def locked(pane_id: str):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(state_path(pane_id).with_suffix(".lock"), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def load(pane_id: str) -> dict | None:
    """The pane's state, None when unarmed. Raises Invalid for a file that exists but is wrong."""
    try:
        text = state_path(pane_id).read_text()
    except FileNotFoundError:
        return None
    try:
        state = json.loads(text)
    except ValueError as e:
        raise Invalid(f"not JSON: {e}") from None
    if not isinstance(state, dict):
        raise Invalid("not an object")
    for key, kind in SCHEMA.items():
        # bool is an int subclass
        if key not in state or not isinstance(state[key], kind) or isinstance(state[key], bool):
            raise Invalid(f"bad or missing {key!r}")
    if state["pane"] != pane_id:
        raise Invalid(f"holds pane {state['pane']!r}")
    return state


def save(pane_id: str, state: dict) -> None:
    path = state_path(pane_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.stem, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        f.write(json.dumps(state, indent=1) + "\n")
    os.replace(tmp, path)


def quarantine(pane_id: str, error: Exception) -> None:
    """Move a corrupt state file aside and tell Greg: the pane is unarmed until re-armed."""
    path = state_path(pane_id)
    os.replace(path, path.with_suffix(".bad"))
    log(pane_id, f"corrupt state moved to {path.with_suffix('.bad')}: {error}")
    notify(pane_id, f"Claude shift state for {pane_id} was corrupt ({short(error)}); pane disarmed, re-arm it.", wait=False)


def notify(pane_id: str, message: str, wait: bool = True) -> None:
    """Best-effort Pushover; a failure is logged, never raised."""
    try:
        if not wait:
            subprocess.Popen([PUSHOVER, "-m", message], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)  # fmt: skip
            return
        out = subprocess.run([PUSHOVER, "-m", message], capture_output=True, text=True, timeout=30)
        # pushover.py exits 0 on an HTTP error
        if out.returncode or "[200]" not in out.stdout:
            log(pane_id, f"pushover failed: {short(out.stdout + out.stderr)}")
    except Exception as e:
        try:
            log(pane_id, f"pushover failed: {short(e)}")
        except Exception:
            pass


def context_tokens(transcript: str | os.PathLike) -> int:
    """Context size at the last main-thread assistant message, read from the file's tail."""
    with open(transcript, "rb") as f:
        size = f.seek(0, os.SEEK_END)
        chunk = 1 << 16
        while True:
            start = max(0, size - chunk)
            f.seek(start)
            lines = f.read(size - start).split(b"\n")
            if start:
                lines = lines[1:]  # partial first line
            for line in reversed(lines):
                if b'"usage"' not in line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                message = entry.get("message") or {}
                usage = message.get("usage")
                if (
                    entry.get("type") != "assistant"
                    or entry.get("isSidechain")
                    or not usage
                    or message.get("model") == "<synthetic>"
                ):
                    continue
                return sum(usage.get(k) or 0 for k in USAGE_KEYS)
            if not start:
                return 0
            chunk *= 4
