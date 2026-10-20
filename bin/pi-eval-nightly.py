#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Run pi-eval.py and Pushover only when cases keep failing.

Alerts when a case fails two nights running, or more than 2 cases fail.
Known-flaky single failures stay quiet. Writes the last report to the log
and keeps failure transcripts under the state dir for 7 days.

Usage:
    pi-eval-nightly.py
    pi-eval-nightly.py --only weather-tomorrow,front-door --no-push --state-dir /tmp/x
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

BIN = Path(__file__).resolve().parent
HOME = Path.home()
SECRETS = BIN.parent / "nixos" / "secrets" / ".env"
KEEP_DAYS = 7
MAX_FAILS_QUIET = 2


def load_secrets() -> dict[str, str]:
    # launchd has no shell env; .zshrc sources this same file.
    env = {}
    if SECRETS.is_file():
        for line in SECRETS.read_text().splitlines():
            key, sep, val = line.partition("=")
            if sep and key.strip().isidentifier():
                env[key.strip()] = val.strip().strip("'\"")
    return env


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def prune(state: Path, today: dt.date) -> None:
    for d in state.iterdir():
        try:
            age = today - dt.date.fromisoformat(d.name)
        except ValueError:
            continue
        if d.is_dir() and age.days > KEEP_DAYS:
            shutil.rmtree(d, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--only", help="comma-separated case names")
    ap.add_argument("--no-push", action="store_true", help="print the alert, send nothing")
    ap.add_argument("--state-dir", type=Path, default=HOME / ".cache" / "pi-eval")
    ap.add_argument("--log", type=Path, default=HOME / "Library" / "Logs" / "pi-eval-nightly.log")
    args = ap.parse_args()

    env = {**os.environ, **load_secrets()}
    today = dt.date.today()
    run_dir = args.state_dir / today.isoformat()
    run_dir.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)

    cmd = [str(BIN / "pi-eval.py"), "--json", "--keep", str(run_dir)]
    if args.only:
        cmd += ["--only", args.only]
    p = subprocess.run(cmd, env=env, capture_output=True, text=True)
    try:
        results = json.loads(p.stdout)["results"]
    except (ValueError, KeyError):
        results = None

    version = subprocess.run(["pi", "--version"], env=env, capture_output=True, text=True)
    version = (version.stdout or version.stderr).strip() or "unknown"
    last_version = args.state_dir / "last-version"
    old_version = last_version.read_text().strip() if last_version.exists() else version
    last_version.write_text(version + "\n")

    stamp = dt.datetime.now().isoformat(timespec="seconds")
    report = [f"{stamp}  pi {version}"]
    if results is None:
        failed, total = ["pi-eval-crashed"], 0
        report += [f"pi-eval exit {p.returncode}", p.stderr.strip()[-2000:]]
    else:
        total = len(results)
        failed = [r["name"] for r in results if not r["pass"]]
        for r in results:
            why = "  " + "; ".join(r["fails"]) if r["fails"] else ""
            report.append(f"{'PASS' if r['pass'] else 'FAIL'}  {r['secs']:>4}s  {r['name']}{why}")
            if r["pass"]:
                (run_dir / f"{r['name']}.jsonl").unlink(missing_ok=True)
    summary = f"{total - len(failed)}/{total} passed" if results is not None else "crashed"
    report.append(summary)
    args.log.write_text("\n".join(report) + "\n")
    print("\n".join(report))

    last_failed = args.state_dir / "last-failed.json"
    prev = set(read_json(last_failed, []))
    last_failed.write_text(json.dumps(failed))
    prune(args.state_dir, today)

    if not (set(failed) & prev or len(failed) > MAX_FAILS_QUIET):
        return 0
    msg = f"pi-eval: {summary} — failed: {', '.join(failed)} (log: ~/Library/Logs/pi-eval-nightly.log)"
    if version != old_version:
        msg += f"; pi changed {old_version} -> {version}"
    if args.no_push:
        print("would push:", msg)
        return 0
    return subprocess.run([str(BIN / "pushover.py"), "-m", msg], env=env).returncode


if __name__ == "__main__":
    sys.exit(main())
