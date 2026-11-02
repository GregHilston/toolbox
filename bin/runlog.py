#!/usr/bin/env python3
"""One JSON line per event, so a swarm run's time can be explained from disk.

    runlog.py start <run>             # point this repo's log at <run>
    runlog.py emit <kind> [k=v ...]   # append one event to the current run
    runlog.py sample [--every 30]     # machine load, CPU, RAM, gates, lanes

Tools import `emit`, which never raises: a logging failure must not stop a lane.
`RUN_LOG_LANE` and `RUN_LOG_TICKET` fill in lane and ticket when a caller omits
them, so a worker's tools inherit both. `RUN_LOG_DIR` moves the cache elsewhere.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

GATE_SLOT_DIR = Path.home() / ".cache" / "gate-slots"


def base_dir() -> Path:
    return Path(os.environ.get("RUN_LOG_DIR", Path.home() / ".cache" / "run-log"))


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True).stdout.strip()
    except OSError:
        return ""


def toplevel() -> str:
    return _git("rev-parse", "--show-toplevel") or os.getcwd()


def repo_name() -> str:
    """The origin's name, so a lane's clone writes to the same log as its repo."""
    url = _git("remote", "get-url", "origin")
    name = Path(url.rstrip("/")).name if url else ""
    if name.endswith(".git"):
        name = name[:-4]
    return name or Path(toplevel()).name or "unknown"


def run_dir() -> Path:
    return base_dir() / repo_name()


def current() -> str | None:
    try:
        name = (run_dir() / "current").read_text().strip()
    except OSError:
        return None
    return name or None


def log_path(run: str) -> Path:
    return run_dir() / f"{run}.jsonl"


def start(run: str) -> Path:
    """Point this repo at a run; a lane's clone resolves to the same file."""
    path = run_dir()
    path.mkdir(parents=True, exist_ok=True)
    tmp = path / "current.tmp"
    tmp.write_text(run + "\n")
    os.replace(tmp, path / "current")
    return log_path(run)


def _ticket(value) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def emit(kind: str, lane: str | None = None, ticket: str | None = None, **fields) -> None:
    """Append one event to the current run's log; never raise."""
    try:
        run = current()
        if not run:
            return
        event = {
            **fields,
            "t": time.time(),
            "kind": kind,
            "lane": lane if lane is not None else os.environ.get("RUN_LOG_LANE") or None,
            "ticket": _ticket(ticket if ticket is not None else os.environ.get("RUN_LOG_TICKET")),
            "worktree": toplevel(),
        }
        line = (json.dumps(event, separators=(",", ":")) + "\n").encode()
        path = log_path(run)
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, line)
        finally:
            os.close(fd)
    except Exception:  # noqa: BLE001 - logging must never break a lane
        pass


def _family(command: str) -> str:
    low = command.lower()
    if "godot" in low:
        return "godot"
    if "pytest" in low:
        return "pytest"
    if re.search(r"(^|[\s/])pi(\s|$)", command):
        return "pi"
    return "other"


def cpu_by_family() -> dict[str, float]:
    totals = {"godot": 0.0, "pytest": 0.0, "pi": 0.0, "other": 0.0}
    try:
        out = subprocess.run(["ps", "-axo", "pcpu=,args="], capture_output=True, text=True).stdout
    except OSError:
        return totals
    for line in out.splitlines():
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        try:
            totals[_family(parts[1])] += float(parts[0])
        except ValueError:
            continue
    return {k: round(v, 1) for k, v in totals.items()}


def free_ram_mb() -> int:
    try:
        if sys.platform == "darwin":
            text = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
            match = re.search(r"page size of (\d+) bytes", text)
            page = int(match.group(1)) if match else 4096
            pages = 0
            for line in text.splitlines():
                if line.startswith(("Pages free:", "Pages speculative:")):
                    pages += int(line.split(":")[1].strip().rstrip("."))
            return round(pages * page / 1_000_000)
        meminfo = Path("/proc/meminfo").read_text()
        match = re.search(r"^MemAvailable:\s+(\d+) kB", meminfo, re.M)
        return round(int(match.group(1)) / 1000) if match else 0
    except (OSError, ValueError):
        return 0


def gates_held() -> int:
    """Slots a lane holds now: the files gateslot.py flocks, tried not taken."""
    directory = Path(os.environ.get("GATE_SLOT_DIR", GATE_SLOT_DIR))
    held = 0
    try:
        files = list(directory.glob("*.lock"))
    except OSError:
        return 0
    for path in files:
        try:
            fd = os.open(path, os.O_RDWR)
        except OSError:
            continue
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                held += 1
            else:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
    return held


def running_lanes() -> int:
    try:
        out = subprocess.run(["ps", "-axo", "args="], capture_output=True, text=True).stdout
    except OSError:
        return 0
    return sum(1 for line in out.splitlines() if "overnight-loop" in line and "ps -axo" not in line)


def machine() -> dict:
    return {
        "load1": round(os.getloadavg()[0], 2),
        "cpu": cpu_by_family(),
        "ram_free_mb": free_ram_mb(),
        "gates_held": gates_held(),
        "lanes": running_lanes(),
    }


def sample(every: float = 30.0) -> int:
    """Append a machine sample until another run becomes current."""
    run = current()
    if not run:
        print("runlog.py: no current run; start one first", file=sys.stderr)
        return 1
    while current() == run:
        emit("machine", **machine())
        time.sleep(every)
    return 0


def _coerce(value: str):
    for cast in (int, float):
        try:
            return cast(value)
        except ValueError:
            pass
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    return value


def main(argv: list[str]) -> int:
    if not argv:
        sys.exit(__doc__.strip())
    cmd, rest = argv[0], argv[1:]
    if cmd == "start":
        if not rest:
            sys.exit("usage: runlog.py start <run>")
        path = start(rest[0])
        print(f"{repo_name()}: run {rest[0]} -> {path}")
        return 0
    if cmd == "emit":
        if not rest:
            sys.exit("usage: runlog.py emit <kind> [k=v ...]")
        fields = {}
        for item in rest[1:]:
            key, _, value = item.partition("=")
            fields[key] = _coerce(value)
        emit(rest[0], **fields)
        return 0
    if cmd == "sample":
        every = 30.0
        if "--every" in rest[:-1]:
            every = float(rest[rest.index("--every") + 1])
        try:
            return sample(every)
        except KeyboardInterrupt:
            return 130
    sys.exit(f"runlog.py: unknown command {cmd!r}; expected start, emit or sample")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
