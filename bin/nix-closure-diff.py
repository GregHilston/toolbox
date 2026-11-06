#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Compare two Nix closures, given as files of store paths, by package and version.

`just diff <host>` uses it to show what a deploy would change. It works from path
lists rather than `nvd`, because nvd needs both closures in the local store, and
copying a remote host's closure in is refused for a user the daemon does not trust.
Paths with no version (config files, scripts) are listed by name.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

# Version starts at the first `-<digit>`.
VERSION = re.compile(r"-(?=\d)")
OUTPUT = re.compile(r"-(bin|dev|lib|man|doc|info|out|static|data|debug|terminfo)$")


def natural(v: str) -> list:
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", v)]


def parse(paths: list[str]) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Map pname -> versions, and unversioned name -> store paths."""
    versions: dict[str, set[str]] = defaultdict(set)
    unversioned: dict[str, set[str]] = defaultdict(set)
    for line in paths:
        path = line.strip()
        base = path.rsplit("/", 1)[-1]
        if not base:
            continue
        name = OUTPUT.sub("", base.split("-", 1)[1] if "-" in base else base)
        parts = VERSION.split(name, maxsplit=1)
        # `099-host-keys.conf` is a file, not version 099.
        if len(parts) == 2 and ("." in parts[1].split("-")[0] or "-" not in parts[1]):
            versions[parts[0]].add(parts[1])
        else:
            unversioned[name].add(path)
    return versions, unversioned


def show(vs: set[str]) -> str:
    return ", ".join(sorted(vs, key=natural))


def diff(old: list[str], new: list[str]) -> str:
    old_v, old_u = parse(old)
    new_v, new_u = parse(new)
    changed = [
        f"  {p}  {show(old_v[p])} -> {show(new_v[p])}"
        for p in sorted(old_v.keys() & new_v.keys())
        if old_v[p] != new_v[p]
    ]
    added = [f"  {p}  {show(new_v[p])}" for p in sorted(new_v.keys() - old_v.keys())]
    added += [f"  {n}" for n in sorted(new_u.keys() - old_u.keys())]
    removed = [f"  {p}  {show(old_v[p])}" for p in sorted(old_v.keys() - new_v.keys())]
    removed += [f"  {n}" for n in sorted(old_u.keys() - new_u.keys())]
    out = []
    for title, rows in (("Changed", changed), ("Added", added), ("Removed", removed)):
        if rows:
            out += [f"{title}:", *rows]
    if not out:
        out.append("No package changes.")
    rebuilt = sum(1 for n in old_u.keys() & new_u.keys() if old_u[n] != new_u[n])
    if rebuilt:
        out.append(f"{rebuilt} unversioned paths rebuilt (configs, scripts).")
    out.append(f"Closure: {len(set(old))} -> {len(set(new))} paths.")
    return "\n".join(out)


def read(path: Path) -> list[str]:
    return [line for line in path.read_text().splitlines() if line.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("old", type=Path, help="store paths of the running system, one per line")
    ap.add_argument("new", type=Path, help="store paths of the new build, one per line")
    args = ap.parse_args()
    print(diff(read(args.old), read(args.new)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
