#!/usr/bin/env python3
"""Fast-forward each host's ~/Git/toolbox to origin/main; print an XO alert when one can't.

The control loop (control-loop.sh) runs this each pass and deduplicates alerts
hourly. It runs the checks at most every 10 min (state file: argv[1]), never
stashes, resets or checks out, and stays silent about a host it cannot reach.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

INTERVAL = 600
REPO = '"$HOME/Git/toolbox"'
SSH = ["ssh", "-o", "ConnectTimeout=10"]
HOSTS = [("moriats", [*SSH, "moriats"], REPO),
         ("foundationts", [*SSH, "foundationts"], REPO),
         ("local", ["bash", "-c"], REPO)]

# Prints "<behind>" then, when behind, "ok" or a reason. A dirty file that
# origin does not touch never stops the fast-forward.
SCRIPT = """cd {repo} || exit 3
git fetch -q || exit 4
n=$(git rev-list --count HEAD..origin/main) || exit 5
echo "$n"
[ "$n" = 0 ] && exit 0
b=$(git branch --show-current)
if [ "$b" != main ]; then echo "on branch ${{b:-detached HEAD}}"
elif ! git merge-base --is-ancestor HEAD origin/main; then echo diverged
elif git merge --ff-only -q origin/main >/dev/null 2>&1; then echo ok
else echo "fast-forward refused, local changes in the way"
fi
"""


def due(state: Path, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    try:
        if now - float(state.read_text()) < INTERVAL:
            return False
    except (OSError, ValueError):
        pass
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(str(now))
    return True


def check(host: tuple[str, list[str], str]) -> str | None:
    name, prefix, repo = host
    try:
        r = subprocess.run([*prefix, SCRIPT.format(repo=repo)], capture_output=True,
                           text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None
    lines = r.stdout.splitlines()
    if r.returncode != 0 or not lines or not lines[0].isdigit():
        return None
    behind = int(lines[0])
    if behind == 0 or lines[1:] == ["ok"]:
        return None
    reason = lines[1] if len(lines) > 1 else "unknown"
    return f"XO toolbox: {name} is {behind} behind origin/main and can't fast-forward ({reason})"


def main(hosts=None, state: Path | None = None) -> int:
    if state is not None and not due(state):
        return 0
    for host in hosts or HOSTS:
        line = check(host)
        if line:
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(state=Path(sys.argv[1]) if len(sys.argv) > 1 else None))
