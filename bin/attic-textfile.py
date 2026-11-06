#!/usr/bin/env python3
"""Write the Attic Nix cache's size and activity for node_exporter's textfile collector.

Reads a copy of atticd's SQLite database (home-lab docs/nix-cache.md), never the live
file: it is in WAL mode inside OrbStack's VM, and a host-side reader's locks don't
reach the writer. The copy holds the cache's signing key, so it lives in a private
temporary directory that is removed at once. A failed read writes attic_up 0.

    attic-textfile.py    write $NODE_EXPORTER_TEXTFILE_DIR/attic.prom; run every 60s
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

DB = Path(os.environ.get("ATTIC_DB") or Path.home() / "home-lab-config/attic/server.db")

GAUGES = {
    "attic_up": "1 if the database copy could be read this run.",
    "attic_objects": "Store paths in the cache.",
    "attic_objects_pushed_24h": "Store paths uploaded in the last 24 hours.",
    "attic_last_push_timestamp_seconds": "When a store path was last uploaded.",
    "attic_last_download_timestamp_seconds": "When a store path was last downloaded.",
    "attic_nar_bytes": "Size of every stored path, uncompressed.",
    "attic_storage_bytes": "Size of the compressed chunks on disk.",
}

# Attic writes UTC as `2026-11-06T19:23:32.238406928+00:00`.
EPOCH = "CAST(strftime('%s', substr({}, 1, 19)) AS INTEGER)"
PER_CACHE = f"""
SELECT c.name, count(o.id),
       sum(o.created_at >= strftime('%Y-%m-%dT%H:%M:%S', 'now', '-1 day')),
       {EPOCH.format('max(o.created_at)')}, {EPOCH.format('max(o.last_accessed_at)')}
FROM cache c LEFT JOIN object o ON o.cache_id = c.id
WHERE c.deleted_at IS NULL GROUP BY c.name
"""


def _stamp(path: Path) -> tuple[int, int] | None:
    try:
        st = path.stat()
    except FileNotFoundError:
        return None
    return st.st_size, st.st_mtime_ns


def read(db: Path) -> list[str]:
    """Sample lines from a copy of `db`. Raises if it can't be read."""
    files = [db.with_name(db.name + s) for s in ("", "-wal")]
    with tempfile.TemporaryDirectory() as tmp:
        before = [_stamp(f) for f in files]
        for src in files:
            if src.exists():
                shutil.copyfile(src, Path(tmp, src.name.replace(db.name, "server.db")))
        # A write mid-copy can tear it.
        if [_stamp(f) for f in files] != before:
            raise RuntimeError("database changed while copying")
        con = sqlite3.connect(Path(tmp, "server.db"))
        try:
            rows = con.execute(PER_CACHE).fetchall()
            nar = con.execute("SELECT coalesce(sum(nar_size), 0) FROM nar WHERE state = 'V'").fetchone()[0]
            disk = con.execute("SELECT coalesce(sum(file_size), 0) FROM chunk WHERE state = 'V'").fetchone()[0]
        finally:
            con.close()
    lines = [f"attic_nar_bytes {nar}", f"attic_storage_bytes {disk}"]
    for name, objects, pushed, last_push, last_download in rows:
        label = f'cache="{name}"'
        lines += [f"attic_objects{{{label}}} {objects}", f"attic_objects_pushed_24h{{{label}}} {pushed or 0}"]
        if last_push is not None:
            lines.append(f"attic_last_push_timestamp_seconds{{{label}}} {last_push}")
        if last_download is not None:
            lines.append(f"attic_last_download_timestamp_seconds{{{label}}} {last_download}")
    return lines


def render(lines: list[str] | None) -> str:
    samples = ["attic_up 1", *lines] if lines is not None else ["attic_up 0"]
    out = []
    for name, help_text in GAUGES.items():
        mine = [s for s in samples if s.split("{")[0].split(" ")[0] == name]
        if mine:
            out += [f"# HELP {name} {help_text}", f"# TYPE {name} gauge", *mine]
    return "\n".join(out) + "\n"


def main() -> None:
    try:
        lines = read(DB)
    except Exception as e:
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        lines = None
    out_dir = Path(os.environ.get("NODE_EXPORTER_TEXTFILE_DIR") or Path.home() / ".local/state/node_exporter")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "attic.prom"
    tmp = out.with_name(f"attic.prom.{os.getpid()}")
    try:
        tmp.write_text(render(lines))
        tmp.replace(out)
    finally:
        tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
