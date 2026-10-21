"""The risk classifier's allowlist passes read-only commands and nothing chained."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "dot" / "claude" / ".claude" / "hooks" / "risk-classify.py"
spec = importlib.util.spec_from_file_location("_risk_classify", HOOK)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
allowed = mod.allowed_by_rule


class TestAllowlist(unittest.TestCase):
    def test_read_only_commands_pass(self):
        for c in ("ls -la", "git status", "git --no-pager log -5", "gh pr view 12", "cat a.txt 2>&1", "git branch -a"):
            self.assertTrue(allowed(c), c)

    def test_writes_and_unknowns_do_not(self):
        for c in ("rm -rf x", "git push", "git branch -D x", "find . -delete", "gh pr merge 1", "curl http://x"):
            self.assertFalse(allowed(c), c)

    def test_chaining_and_redirects_do_not(self):
        for c in ("ls; rm x", "cat a | sh", "echo hi > f", "ls $(rm x)", "ls && rm x"):
            self.assertFalse(allowed(c), c)
