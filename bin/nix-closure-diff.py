#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Compare two Nix closures, given as files of store paths, by package and version.

`just diff <host>` uses it to show what a deploy would change. It works from path
lists rather than `nvd`, because nvd needs both closures in the local store, and
copying a remote host's closure in is refused for a user the daemon does not trust.
Paths with no version (config files, scripts) are only counted.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

# nixpkgs names are `pname-version`; the version starts at the first `-<digit>`.
VERSION = re.compile(r"-(?=\d)")


def parse(paths: list[str]) -> tuple[dict[str, set[str]], set[str]]:
    """Map pname -> versions, plus the set of unversioned names."""
    versions: dict[str, set[str]] = defaultdict(set)
    unversioned: set[str] = set()
    for line in paths:
        base = line.strip().rsplit("/", 1)[-1]
        if not base:
            continue
        name = base.split("-", 1)[1] if "-" in base else base
        parts = VERSION.split(name, maxsplit=1)
        if len(parts) == 2:
            versions[parts[0]].add(parts[1])
        else:
            unversioned.add(line.strip())
    return versions, unversioned


def diff(old: list[str], new: list[str]) -> str:
    old_v, old_u = parse(old)
    new_v, new_u = parse(new)
    changed = [
        f"  {p}  {', '.join(sorted(old_v[p]))} -> {', '.join(sorted(new_v[p]))}"
        for p in sorted(old_v.keys() & new_v.keys())
        if old_v[p] != new_v[p]
    ]
    added = [f"  {p}  {', '.join(sorted(new_v[p]))}" for p in sorted(new_v.keys() - old_v.keys())]
    removed = [f"  {p}  {', '.join(sorted(old_v[p]))}" for p in sorted(old_v.keys() - new_v.keys())]
    out = []
    for title, rows in (("Changed", changed), ("Added", added), ("Removed", removed)):
        if rows:
            out += [f"{title}:", *rows]
    if not out:
        out.append("No package changes.")
    others = len(old_u ^ new_u)
    if others:
        out.append(f"{others} unversioned paths differ (configs, scripts).")
    out.append(f"Closure: {len(set(old))} -> {len(set(new))} paths.")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("old", type=Path, help="store paths of the running system, one per line")
    ap.add_argument("new", type=Path, help="store paths of the new build, one per line")
    args = ap.parse_args()
    read = lambda p: [line for line in p.read_text().splitlines() if line.strip()]  # noqa: E731
    print(diff(read(args.old), read(args.new)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
