"""The no-build-on-dungeon hook spots build and test commands, and only those."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "dot" / "claude" / ".claude" / "hooks" / "no-build-on-dungeon.py"
spec = importlib.util.spec_from_file_location("_no_build_on_dungeon", HOOK)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

BLOCKED = [
    "nix build .#darwinConfigurations.moria.system",
    "nix build --no-link --print-out-paths .#x",
    "/nix/var/nix/profiles/default/bin/nix build x",
    "nix --extra-experimental-features flakes build x",
    "nix flake check",
    "cd nixos && nix flake check",
    "nix develop ./nixos -c git commit",
    "just validate",
    "cd nixos && just diff dungeon .",
    "just test",
    "just dr dungeon",
    "nh darwin switch .",
    "darwin-rebuild check --flake .#dungeon",
    "nix-build default.nix",
    "export PATH=/x:$PATH && nix build x",
    "FOO=1 nix build x",
    "timeout 600 nix flake check",
    "caffeinate -i just validate",
    "bash -c 'nix build x'",
    "ls; just validate > /tmp/log 2>&1",
]

ALLOWED = [
    "nix eval --raw .#x",
    "nix flake lock",
    "nix shell nixpkgs#gitleaks -c gitleaks dir x",
    "nix fmt .",
    "ssh moria 'cd /tmp/x/nixos && just validate'",
    "ssh -o ConnectTimeout=10 moria 'nix build x'",
    "git commit -m 'run nix build on moria'",
    "echo just validate",
    "just secrets",
    "just list-hosts",
    "grep 'nix build' README.md",
]


class Refusal(unittest.TestCase):
    def test_blocked(self) -> None:
        for command in BLOCKED:
            with self.subTest(command=command):
                self.assertIsNotNone(hook.refusal(command))

    def test_allowed(self) -> None:
        for command in ALLOWED:
            with self.subTest(command=command):
                self.assertIsNone(hook.refusal(command))


if __name__ == "__main__":
    unittest.main()
