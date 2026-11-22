#!/usr/bin/env python3
"""Add git worktrees to Spotlight's exclusion list; runs as root.

    spotlight-exclude-worktrees.py HOME [--plist PATH] [--dry-run]

Spotlight has no globs, so this expands them and writes the paths into
Exclusions in the Data volume's VolumeConfiguration.plist. Excluded: any
directory under HOME/Git or a worktrees folder whose `.git` is a file, the
worktrees folders themselves, and /private/tmp/lp-*. Prints nothing when the
list is already current.
"""

from __future__ import annotations

import argparse
import plistlib
import sys
from pathlib import Path

PLIST = "/System/Volumes/Data/.Spotlight-V100/VolumeConfiguration.plist"
TMP_GLOB = "lp-*"


def worktrees(home: Path) -> list[str]:
    git = home / "Git"
    folders = [p for p in [*git.glob("*/worktrees"), *git.glob("*-worktrees")] if p.is_dir()]
    candidates = [*git.iterdir(), *(c for f in folders for c in f.iterdir())]
    candidates += Path("/private/tmp").glob(TMP_GLOB)
    found = [str(p) for p in candidates if p.is_dir() and (p / ".git").is_file()]
    return sorted({*found, *map(str, folders)})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("home", type=Path)
    ap.add_argument("--plist", default=PLIST)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    want = worktrees(args.home)
    path = Path(args.plist)
    conf = plistlib.loads(path.read_bytes())
    have = conf.get("Exclusions", [])
    # Spotlight keeps whatever else is in the list (Privacy entries).
    missing = [p for p in want if p not in have]
    if not missing:
        return 0
    print(f"excluding {len(missing)} paths")
    if args.dry_run:
        print("\n".join(missing))
        return 0
    conf["Exclusions"] = [*have, *missing]
    path.write_bytes(plistlib.dumps(conf, fmt=plistlib.FMT_XML))
    return 0


if __name__ == "__main__":
    sys.exit(main())
