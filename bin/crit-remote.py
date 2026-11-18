#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Open a crit review running on another host, over an SSH tunnel.

    crit-remote.py <host>          pick a live review, forward it, open the browser
    crit-remote.py <host> --list   list live reviews only

crit has no login, so it stays on the host's 127.0.0.1; nothing is exposed on
the network. Live reviews come from the host's ~/.crit/sessions/*.json, keeping
those whose daemon pid is still alive. The tunnel runs until Ctrl-C.
"""

from __future__ import annotations

import argparse
import json
import shutil
import socket
import subprocess
import sys

# Prints each session file, then the pids still alive.
REMOTE = r"""
for f in ~/.crit/sessions/*.json; do [ -f "$f" ] && cat "$f" && echo; done
echo '---ALIVE---'
for f in ~/.crit/sessions/*.json; do
  [ -f "$f" ] || continue
  p=$(sed -n 's/.*"pid": *\([0-9]*\).*/\1/p' "$f")
  [ -n "$p" ] && kill -0 "$p" 2>/dev/null && echo "$p"
done
"""


def parse_sessions(out: str) -> list[dict]:
    body, _, alive = out.partition("---ALIVE---")
    pids = {int(p) for p in alive.split()}
    dec = json.JSONDecoder()
    sessions, i = [], 0
    while (i := _skip_ws(body, i)) < len(body):
        obj, i = dec.raw_decode(body, i)
        if obj.get("pid") in pids and obj.get("port"):
            sessions.append(obj)
    return sorted(sessions, key=lambda s: s.get("started_at", ""), reverse=True)


def _skip_ws(s: str, i: int) -> int:
    while i < len(s) and s[i].isspace():
        i += 1
    return i


def label(s: dict) -> str:
    where = s.get("cwd", "?")
    branch = s.get("branch")
    files = " ".join(s.get("args") or [])
    return " ".join(x for x in (where, f"[{branch}]" if branch else "", files) if x)


def free_port(preferred: int) -> int:
    for port in (preferred, 0):
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return sock.getsockname()[1]
    raise RuntimeError("no free local port")


def opener() -> list[str] | None:
    for cmd in ("open", "wslview", "xdg-open"):
        if shutil.which(cmd):
            return [cmd]
    return None


def pick(sessions: list[dict]) -> dict:
    if len(sessions) == 1:
        return sessions[0]
    for n, s in enumerate(sessions, 1):
        print(f"  {n}. {label(s)}")
    choice = input("Review number: ").strip()
    return sessions[int(choice) - 1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("host")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    r = subprocess.run(["ssh", a.host, "sh", "-s"], input=REMOTE, capture_output=True, text=True)
    if r.returncode not in (0, 1):
        print(r.stderr.strip() or f"ssh {a.host} failed", file=sys.stderr)
        return 2
    sessions = parse_sessions(r.stdout)
    if not sessions:
        print(f"No live crit reviews on {a.host}")
        return 1
    if a.list:
        for s in sessions:
            print(f"{s['port']}\t{label(s)}")
        return 0

    s = pick(sessions)
    local = free_port(s["port"])
    url = f"http://localhost:{local}/"
    tunnel = subprocess.Popen(
        ["ssh", "-N", "-o", "ExitOnForwardFailure=yes", "-L", f"{local}:127.0.0.1:{s['port']}", a.host]
    )
    print(f"{label(s)}\n{url}  (Ctrl-C to close)")
    if cmd := opener():
        subprocess.run([*cmd, url], check=False)
    try:
        return tunnel.wait()
    except KeyboardInterrupt:
        tunnel.terminate()
        return 0


if __name__ == "__main__":
    sys.exit(main())
