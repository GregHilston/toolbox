#!/usr/bin/env python3
"""Claude Code status line: post rate_limits to the dradis core, then print ccstatusline.

Reads the status-line JSON on stdin, passes the same bytes to ccstatusline and prints
its output unchanged. The post goes to a detached child, at most once a minute, so a
slow or dead core never holds the status line. Env: DRADIS_URL, DRADIS_HOST,
CCSTATUSLINE (binary), STATUSLINE_POST_STAMP (stamp file).
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

DEFAULT_URL = "https://dungeon.tail1b9d9.ts.net:10000"
DEFAULT_CCSTATUSLINE = "~/.npm-global/bin/ccstatusline"
INTERVAL_S = 60
TIMEOUT_S = 1


def stamp_path() -> Path:
    return Path(os.environ.get("STATUSLINE_POST_STAMP") or "~/.cache/statusline-post/last").expanduser()


def due(stamp: Path, now: float) -> bool:
    try:
        return now - stamp.stat().st_mtime >= INTERVAL_S
    except OSError:
        return True


def body_for(raw: bytes) -> bytes | None:
    try:
        limits = json.loads(raw).get("rate_limits")
        if not limits:
            return None
        host = os.environ.get("DRADIS_HOST") or socket.gethostname().split(".")[0]
        return json.dumps(
            {"host": host, "five_hour": limits.get("five_hour"), "seven_day": limits.get("seven_day")}
        ).encode()
    except (ValueError, AttributeError):
        return None


def spawn_post(body: bytes) -> None:
    child = subprocess.Popen(
        [sys.executable, __file__, "--post"],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    assert child.stdin is not None
    child.stdin.write(body)
    child.stdin.close()


def post(body: bytes) -> None:
    url = (os.environ.get("DRADIS_URL") or DEFAULT_URL) + "/quota/claude"
    request = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(request, timeout=TIMEOUT_S).close()
    except Exception:  # a dead core stays out of the status line
        pass


def main() -> int:
    if sys.argv[1:] == ["--post"]:
        post(sys.stdin.buffer.read())
        return 0

    raw = sys.stdin.buffer.read()
    try:
        body = body_for(raw)
        stamp = stamp_path()
        if body and due(stamp, time.time()):
            stamp.parent.mkdir(parents=True, exist_ok=True)
            stamp.touch()
            spawn_post(body)
    except Exception:  # the status line outlives any failure here
        pass

    binary = os.environ.get("CCSTATUSLINE") or os.path.expanduser(DEFAULT_CCSTATUSLINE)
    try:
        out = subprocess.run([binary], input=raw, stdout=subprocess.PIPE, check=False).stdout
    except OSError:
        return 0
    sys.stdout.buffer.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
