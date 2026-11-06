"""attic-textfile.py reads a copy of the WAL database and writes attic_up 0 on failure."""

from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load

mod = load("attic-textfile.py")

SCHEMA = """
CREATE TABLE cache (id INTEGER PRIMARY KEY, name TEXT, deleted_at TEXT);
CREATE TABLE object (id INTEGER PRIMARY KEY, cache_id INT, created_at TEXT, last_accessed_at TEXT);
CREATE TABLE nar (id INTEGER PRIMARY KEY, state TEXT, nar_size INT);
CREATE TABLE chunk (id INTEGER PRIMARY KEY, state TEXT, file_size INT);
"""


class TestAtticTextfile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name, "server.db")
        con = sqlite3.connect(self.db)
        con.execute("PRAGMA journal_mode=WAL")
        con.executescript(SCHEMA)
        con.executescript("""
            INSERT INTO cache VALUES (1, 'darwin', NULL), (2, 'gone', '2026-01-01T00:00:00+00:00');
            INSERT INTO object VALUES
              (1, 1, '2020-01-01T00:00:00.5+00:00', NULL),
              (2, 1, '2020-01-02T00:00:10.123456789+00:00', '2020-01-03T00:00:00+00:00');
            INSERT INTO nar VALUES (1, 'V', 100), (2, 'P', 999);
            INSERT INTO chunk VALUES (1, 'V', 40), (2, 'V', 2);
        """)
        con.commit()
        # Left open, so the rows sit in the WAL file.
        self.writer = con

    def tearDown(self):
        self.writer.close()
        self.tmp.cleanup()

    def test_reads_rows_still_in_the_wal(self):
        self.assertTrue(Path(str(self.db) + "-wal").stat().st_size > 0)
        lines = mod.read(self.db)
        self.assertIn('attic_objects{cache="darwin"} 2', lines)
        self.assertIn("attic_nar_bytes 100", lines)
        self.assertIn("attic_storage_bytes 42", lines)
        self.assertIn('attic_last_push_timestamp_seconds{cache="darwin"} 1577923210', lines)
        self.assertIn('attic_last_download_timestamp_seconds{cache="darwin"} 1578009600', lines)
        self.assertIn('attic_objects_pushed_24h{cache="darwin"} 0', lines)
        self.assertFalse(any('"gone"' in line for line in lines))

    def test_empty_cache_has_no_timestamps(self):
        self.writer.execute("DELETE FROM object")
        self.writer.commit()
        lines = mod.read(self.db)
        self.assertIn('attic_objects{cache="darwin"} 0', lines)
        self.assertFalse(any("timestamp" in line for line in lines))

    def test_unreadable_database_writes_up_zero(self):
        with tempfile.TemporaryDirectory() as out, mock.patch.object(mod, "DB", Path(out, "missing.db")), \
                mock.patch.dict(os.environ, {"NODE_EXPORTER_TEXTFILE_DIR": out}), mock.patch("sys.stderr"):
            mod.main()
            text = Path(out, "attic.prom").read_text()
        self.assertIn("attic_up 0", text)
        self.assertNotIn("attic_objects", text)

    def test_render_types_every_sample(self):
        text = mod.render(mod.read(self.db))
        for line in text.splitlines():
            if not line.startswith("#"):
                self.assertIn(f"# TYPE {line.split('{')[0].split(' ')[0]} gauge", text)


if __name__ == "__main__":
    unittest.main()
