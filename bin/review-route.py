#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Say who reviews a branch: none, deepseek or sonnet.

    review-route.py [BRANCH] [--base main] [--repo DIR]

none: only tests, data or docs changed. sonnet: the diff touches the UI, which
needs screenshots DeepSeek cannot read. deepseek: everything else. The reviewer
is `pi-ask.py`, or a Sonnet subagent for sonnet. Conflicts go to Sonnet whatever
this says.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

QUIET = re.compile(r"(^|/)tests?/|\.(jsonc?|md|txt)$")
UI = re.compile(r"\.(tscn|tres|png|svg|css|html)$|(^|/)(shell|ui|dashboard)/")


def route(files: list[str]) -> str:
    """none, sonnet or deepseek for a list of changed paths."""
    if all(QUIET.search(f) for f in files):
        return "none"
    return "sonnet" if any(UI.search(f) for f in files) else "deepseek"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("branch", nargs="?", default="HEAD")
    p.add_argument("--base", default="main")
    p.add_argument("--repo", default=".")
    args = p.parse_args()
    proc = subprocess.run(["git", "diff", "--name-only", f"{args.base}...{args.branch}"],
                          cwd=args.repo, capture_output=True, text=True)
    if proc.returncode:
        print(proc.stderr.strip(), file=sys.stderr)
        return 2
    print(route(proc.stdout.split()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
