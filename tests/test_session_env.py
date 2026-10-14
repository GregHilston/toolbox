"""The SessionStart hook that gives Claude Code's Bash tool the toolbox PATH."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / "dot" / "claude" / ".claude" / "hooks" / "session-env.sh"


class TestSessionEnv(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.env_file = Path(self.tmp.name) / "env.sh"
        self.env = dict(os.environ, CLAUDE_ENV_FILE=str(self.env_file), TOOLBOX_HOME=str(REPO))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_hook(self) -> None:
        subprocess.run([str(HOOK)], env=self.env, check=True)

    def test_a_command_run_after_the_env_file_finds_toolbox_scripts(self):
        self.run_hook()
        # The snapshot's PATH, with no toolbox in it.
        out = subprocess.run(["/bin/sh", "-c", f". {self.env_file}; command -v pi-ask.py"],
                             env={"PATH": "/usr/bin:/bin", "HOME": self.tmp.name},
                             capture_output=True, text=True)
        self.assertEqual(out.stdout.strip(), str(REPO / "bin" / "pi-ask.py"), out.stderr)

    def test_writes_once_however_often_the_session_restarts(self):
        self.run_hook()
        self.run_hook()
        self.assertEqual(self.env_file.read_text().count("export PATH"), 1)

    def test_names_the_secrets_file_without_copying_it(self):
        self.run_hook()
        text = self.env_file.read_text()
        self.assertIn("nixos/secrets/.env", text)
        self.assertNotIn("API_KEY", text)

    def test_does_nothing_outside_a_session_start(self):
        env = dict(self.env)
        env.pop("CLAUDE_ENV_FILE")
        subprocess.run([str(HOOK)], env=env, check=True)
        self.assertFalse(self.env_file.exists())


if __name__ == "__main__":
    unittest.main()
