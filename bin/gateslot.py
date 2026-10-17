"""A machine-wide counting semaphore for ./verify.sh gates.

Lanes spend most of their time coding; the gate is the one CPU-heavy step.
Each slot is a flock'd file, so a crashed holder frees its slot by dying.

    from gateslot import slot
    with slot(): ...                  # a lane gate waits for one of GATE_SLOTS
    with slot(land=True): ...         # a landing gate also has a reserved slot

    gateslot.py [--land] -- ./verify.sh    # same, from a shell

GATE_SLOTS sets the count (default 2); 0 turns the queue off.
"""

import fcntl
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

DIR = Path(os.environ.get("GATE_SLOT_DIR", Path.home() / ".cache" / "gate-slots"))


@contextmanager
def slot(land: bool = False, poll: float = 2.0):
    n = int(os.environ.get("GATE_SLOTS", "2"))
    if n <= 0:
        yield
        return
    DIR.mkdir(parents=True, exist_ok=True)
    held = None
    while held is None:
        for i in range(n + land):
            f = open(DIR / f"{i}.lock", "w")
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                held = f
                break
            except BlockingIOError:
                f.close()
        else:
            time.sleep(poll)
    try:
        yield
    finally:
        held.close()


if __name__ == "__main__":
    args = sys.argv[1:]
    land = args[:1] == ["--land"]
    cmd = args[args.index("--") + 1:] if "--" in args else []
    if not cmd:
        sys.exit("usage: gateslot.py [--land] -- cmd...")
    with slot(land):
        sys.exit(subprocess.run(cmd).returncode)
