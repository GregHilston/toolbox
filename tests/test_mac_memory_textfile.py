"""mac-memory-textfile.sh reads vm_stat and sysctl right, and survives a failed extra.

The alert on dungeon depends on the swap counters, so an optional reading that fails
must not take them down with it.
"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "bin" / "mac-memory-textfile.sh"

VM_STAT = """Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                                6478.
Swapins:                                    100.
Swapouts:                                   250.
"""

PS = """  10 /Applications/OrbStack.app/Contents/Frameworks/OrbStack Helper.app/Contents/MacOS/OrbStack Helper
  11 /Users/me/.local/share/claude/versions/2.1.299
  12 /Users/me/.local/share/claude/versions/2.1.299
  13 omlx-server
  14 /usr/sbin/bluetoothd
"""

TOP = """Processes: 5 total
PID    MEM
10     9741M
11     200M+
12     1G
13     21G
14     512K
"""


def run(memory_pressure: str, top: str = f"cat <<'X'\n{TOP}X") -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as tmp:
        stubs = Path(tmp, "stubs")
        stubs.mkdir()
        for name, body in {
            "vm_stat": f"cat <<'X'\n{VM_STAT}X",
            "sysctl": "echo 2",
            "memory_pressure": memory_pressure,
            "ps": f"cat <<'X'\n{PS}X",
            "top": top,
        }.items():
            (stubs / name).write_text(f"#!/bin/sh\n{body}\n")
            (stubs / name).chmod(0o755)
        out = Path(tmp, "out")
        env = {"PATH": f"{stubs}:/usr/bin:/bin", "HOME": tmp, "NODE_EXPORTER_TEXTFILE_DIR": str(out)}
        rc = subprocess.run(["/bin/bash", str(SCRIPT)], env=env, capture_output=True).returncode
        prom = out / "memory.prom"
        leftovers = [p.name for p in out.iterdir() if p.name != "memory.prom"]
        return rc, (prom.read_text() if prom.exists() else "") + "".join(leftovers)


class TestMacMemoryTextfile(unittest.TestCase):
    def test_counters_are_pages_times_page_size(self):
        rc, prom = run('echo "System-wide memory free percentage: 37%"')
        self.assertEqual(rc, 0)
        self.assertIn("mac_memory_swapins_bytes_total 1638400", prom)
        self.assertIn("mac_memory_swapouts_bytes_total 4096000", prom)
        self.assertIn("mac_memory_pressure_level 2", prom)
        self.assertIn("mac_memory_free_percent 37", prom)

    def test_a_failed_memory_pressure_keeps_the_swap_counters(self):
        rc, prom = run("exit 1")
        self.assertEqual(rc, 0)
        self.assertIn("mac_memory_swapins_bytes_total 1638400", prom)
        self.assertNotIn("mac_memory_free_percent", prom)
        self.assertNotIn(".prom.", prom, "a temp file was left behind")

    def test_footprint_is_summed_per_app(self):
        rc, prom = run("exit 1")
        self.assertEqual(rc, 0)
        self.assertIn('mac_process_memory_bytes{app="OrbStack"} 10214178816', prom)
        self.assertIn('mac_process_memory_bytes{app="claude"} 1283457024', prom)
        self.assertIn('mac_process_memory_bytes{app="omlx-server"} 22548578304', prom)
        self.assertIn('mac_process_memory_bytes{app="other"} 524288', prom)

    def test_a_failed_top_keeps_the_swap_counters(self):
        rc, prom = run("exit 1", top="exit 1")
        self.assertEqual(rc, 0)
        self.assertIn("mac_memory_swapins_bytes_total 1638400", prom)


if __name__ == "__main__":
    unittest.main()
