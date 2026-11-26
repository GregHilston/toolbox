"""The global CLAUDE.md must not import RTK.md; the rtk hook covers it."""

from __future__ import annotations

import unittest
from pathlib import Path

GLOBAL = Path(__file__).resolve().parent.parent / "dot" / "claude" / ".claude" / "CLAUDE.md"


class GlobalClaudeMd(unittest.TestCase):
    def test_no_rtk_import(self) -> None:
        self.assertNotIn("@RTK.md", GLOBAL.read_text())


if __name__ == "__main__":
    unittest.main()
