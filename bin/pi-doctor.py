#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check that this host's pi fallback setup is intact. No LLM calls.

Checks the ~/.pi/agent links into the toolbox repo, lab-alerts and netcheck
on PATH, toolbox and home-lab not behind origin/main, and pi --version.
Exit 1 on any problem.

Usage:
    pi-doctor.py
    pi-doctor.py --push    # one Pushover when something is wrong
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

BIN = Path(__file__).resolve().parent
TOOLBOX = BIN.parent
HOME = Path.home()
SECRETS = TOOLBOX / "nixos" / "secrets" / ".env"
AGENT = HOME / ".pi" / "agent"
LINKED = ["AGENTS.md", "prompts", "extensions/gateway-fallback.ts", "pi-fff.json"]
TOOLS = ["lab-alerts", "netcheck"]
REPOS = [TOOLBOX, HOME / "Git" / "home-lab"]


def load_secrets() -> dict[str, str]:
    # launchd has no shell env; .zshrc sources this same file.
    env = {}
    if SECRETS.is_file():
        for line in SECRETS.read_text().splitlines():
            key, sep, val = line.partition("=")
            if sep and key.strip().isidentifier():
                env[key.strip()] = val.strip().strip("'\"")
    return env


def check_links(agent: Path, repo: Path) -> list[str]:
    src = (repo / "dot" / "pi" / ".pi" / "agent").resolve()
    out = []
    for rel in LINKED:
        p = agent / rel
        if not p.exists():
            out.append(f"{p} missing")
        elif not p.resolve().is_relative_to(src):
            out.append(f"{p} is not linked into {src}")
    return out


def check_tools(names: list[str]) -> list[str]:
    return [f"{n} not on PATH" for n in names if not shutil.which(n)]


def check_repo(repo: Path) -> list[str]:
    def git(*a: str):
        return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, timeout=60)

    if not repo.is_dir():
        return [f"{repo} missing"]
    fetch = git("fetch", "--quiet", "origin", "main")
    if fetch.returncode:
        return [f"{repo.name}: git fetch failed: {fetch.stderr.strip()[-120:]}"]
    n = git("rev-list", "--count", "HEAD..origin/main").stdout.strip()
    return [f"{repo.name} is {n} commits behind origin/main"] if n not in ("", "0") else []


def check_pi() -> tuple[list[str], str]:
    if not shutil.which("pi"):
        return ["pi not on PATH"], ""
    p = subprocess.run(["pi", "--version"], capture_output=True, text=True, timeout=30)
    ver = (p.stdout or p.stderr).strip()
    return ([] if p.returncode == 0 and ver else [f"pi --version failed ({p.returncode})"]), ver


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--push", action="store_true", help="Pushover once if anything is wrong")
    args = ap.parse_args()

    host = os.uname().nodename.split(".")[0]
    problems = check_links(AGENT, TOOLBOX) + check_tools(TOOLS)
    for r in REPOS:
        problems += check_repo(r)
    pi_problems, version = check_pi()
    problems += pi_problems

    print(f"pi-doctor on {host}, pi {version or 'unknown'}")
    print("\n".join(f"PROBLEM  {p}" for p in problems) if problems else "ok")
    if problems and args.push:
        msg = f"pi-doctor {host}: " + "; ".join(problems)
        subprocess.run([str(BIN / "pushover.py"), "-m", msg[:900]], env={**os.environ, **load_secrets()})
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
