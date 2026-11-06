"""nix-closure-diff.py reports version changes, additions and removals by package."""

from __future__ import annotations

import unittest

from _loader import load

ncd = load("nix-closure-diff.py")

OLD = [
    "/nix/store/aaaa-neovim-0.12.5",
    "/nix/store/bbbb-git-2.55.0",
    "/nix/store/cccc-python3-3.14.8-env",
    "/nix/store/dddd-etc",
    "/nix/store/eeee-ripgrep-15.0.0",
    "/nix/store/iiii-curl-8.22.0",
    "/nix/store/jjjj-curl-8.22.0-man",
    "/nix/store/kkkk-openssl-3.5.9",
]
NEW = [
    "/nix/store/ffff-neovim-0.12.6",
    "/nix/store/bbbb-git-2.55.0",
    "/nix/store/cccc-python3-3.14.8-env",
    "/nix/store/gggg-etc",
    "/nix/store/hhhh-comma-with-db-2.4.2",
    "/nix/store/iiii-curl-8.22.0",
    "/nix/store/llll-openssl-3.5.10",
    "/nix/store/mmmm-org.nixos.nh-clean.plist",
    "/nix/store/nnnn-099-host-keys.conf",
]


class Diff(unittest.TestCase):
    def setUp(self) -> None:
        self.out = ncd.diff(OLD, NEW)

    def test_version_change(self) -> None:
        self.assertIn("neovim  0.12.5 -> 0.12.6", self.out)

    def test_added_and_removed(self) -> None:
        self.assertIn("Added:\n  comma-with-db  2.4.2", self.out)
        self.assertIn("Removed:\n  ripgrep  15.0.0", self.out)

    def test_unchanged_package_not_listed(self) -> None:
        self.assertNotIn("git", self.out)

    def test_version_with_suffix_stays_whole(self) -> None:
        self.assertNotIn("python3", self.out)

    def test_unversioned_rebuild_counted_once(self) -> None:
        self.assertIn("1 unversioned paths rebuilt", self.out)

    def test_unversioned_addition_named(self) -> None:
        self.assertIn("  org.nixos.nh-clean.plist\n", self.out)

    def test_output_suffix_is_not_a_version(self) -> None:
        self.assertNotIn("curl", self.out)

    def test_digit_led_file_is_not_versioned(self) -> None:
        self.assertIn("  099-host-keys.conf", self.out)

    def test_versions_sort_naturally(self) -> None:
        self.assertIn("openssl  3.5.9 -> 3.5.10", self.out)

    def test_same_closure(self) -> None:
        self.assertTrue(ncd.diff(OLD, OLD).startswith("No package changes."))


if __name__ == "__main__":
    unittest.main()
