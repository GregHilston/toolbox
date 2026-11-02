#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Report what in this repo is out of date, vulnerable or undeployed. Read-only.

Dependabot's silence proves little: on 2026-11-02 it had zero alerts while
`npm audit` flagged 8 packages, so this checks the lockfiles itself. Homebrew
pi bundles its own dependencies, which no lockfile here covers.

Only dungeon and moria are checked. A host counts as on the lock when its
system was built from the locked nix-darwin rev. Comparing the full store path
would need a slow eval, so this misses a config-only change.

Exit codes: 0 nothing to do, 1 something wants attention, 2 could not tell.
"""

from __future__ import annotations

import json
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MACS = ("dungeon", "moria")
OWNER_REPO = "GregHilston/toolbox"
STALE_LOCK_DAYS = 14
# Brackets stop pgrep matching this probe's shell.
HOST_PROBE = (
    "uptime; echo ---; readlink /run/current-system; echo ---; "
    "pgrep -fl 'darwin-rebuil[d]|nix buil[d]|nixos-rebuil[d]' || true"
)


def audit_failed(report: dict) -> bool:
    # A network failure is valid JSON, without metadata.
    return "vulnerabilities" not in report.get("metadata", {})


def security_updates_on(settings: dict) -> bool:
    return bool(settings.get("enabled")) and not settings.get("paused")


def newest_runs(runs: list[dict]) -> dict[str, dict]:
    newest: dict[str, dict] = {}
    for entry in runs:
        newest.setdefault(entry["workflowName"], entry)
    return newest


def audit_needs_attention(report: dict) -> bool:
    counts = report.get("metadata", {}).get("vulnerabilities", {})
    return bool(counts.get("high") or counts.get("critical"))


def audit_line(where: str, report: dict) -> str:
    total = report.get("metadata", {}).get("vulnerabilities", {}).get("total", 0)
    if not total:
        return f"{where}: clean"
    # A string in `via` means inherited from another listed package.
    own = [
        f"{name} ({entry['severity']})"
        for name, entry in report.get("vulnerabilities", {}).items()
        if any(isinstance(via, dict) for via in entry.get("via", []))
    ]
    return f"{where}: {total} flagged, {', '.join(own)}"


def root_input(lock: dict, name: str) -> dict:
    # "nixpkgs" can name a transitive copy, not ours.
    nodes = lock["nodes"]
    return nodes[nodes[lock["root"]]["inputs"][name]]["locked"]


def lock_age_days(lock: dict, now: float) -> int:
    return int((now - root_input(lock, "nixpkgs")["lastModified"]) // 86400)


def locked_darwin_rev(lock: dict) -> str:
    return root_input(lock, "darwin")["rev"]


def on_lock(system_path: str, darwin_rev: str) -> bool:
    label = system_path.rsplit(".", 1)[-1] if system_path else ""
    return bool(label) and darwin_rev.startswith(label)


def load_average(uptime: str) -> float | None:
    match = re.search(r"load averages?: *([\d.]+)", uptime)
    return float(match.group(1)) if match else None


def parse_probe(out: str) -> dict:
    parts = (out.split("---\n") + ["", "", ""])[:3]
    return {
        "load": load_average(parts[0]),
        "system": parts[1].strip(),
        "builds": [line for line in parts[2].splitlines() if line.strip()],
    }


def branch_tracking_actions(workflow_text: str) -> list[str]:
    return re.findall(r"uses:\s*(\S+@(?:main|master))\b", workflow_text)


def pin_is_behind(pins: set[str], latest: str) -> bool:
    return pins != {latest}


def exit_code(attention: int, unknown: int) -> int:
    return 1 if attention else 2 if unknown else 0


class Report:
    def __init__(self) -> None:
        self.attention = 0
        self.unknown = 0

    def section(self, title: str) -> None:
        print(f"\n{title}")

    def ok(self, text: str) -> None:
        print(f"  ok    {text}")

    def flag(self, text: str) -> None:
        self.attention += 1
        print(f"  LOOK  {text}")

    def cannot_tell(self, text: str) -> None:
        self.unknown += 1
        print(f"  ????  {text}")

    def note(self, text: str) -> None:
        print(f"  note  {text}")

    def verdict(self, needs_attention: bool, text: str) -> None:
        (self.flag if needs_attention else self.ok)(text)


def guarded(report: Report, check, *args) -> None:
    try:
        check(report, *args)
    except (OSError, KeyError, ValueError, TypeError, AttributeError) as err:
        report.cannot_tell(f"{check.__name__} broke: {type(err).__name__}: {err}")


def run(cmd: list[str], cwd: Path = REPO, timeout: int = 60) -> str | None:
    try:
        done = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


def run_json(cmd: list[str], cwd: Path = REPO, timeout: int = 60):
    out = run(cmd, cwd, timeout)
    try:
        return json.loads(out) if out else None
    except json.JSONDecodeError:
        return None


def npm_latest(package: str) -> str | None:
    out = run(["npm", "view", package, "version"])
    return out.strip() if out else None


def check_hosts(report: Report, lock: dict) -> None:
    report.section("Hosts")
    rev = locked_darwin_rev(lock)
    here = socket.gethostname().split(".")[0]
    for host in MACS:
        if host == here:
            out = run(["sh", "-c", HOST_PROBE], timeout=20)
        else:
            out = run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=6", host, HOST_PROBE], timeout=20)
        if out is None:
            report.cannot_tell(f"{host}: unreachable")
            continue
        probe = parse_probe(out)
        report.verdict(not on_lock(probe["system"], rev), f"{host}: system {probe['system'][-30:]}, lock has {rev[:7]}")
        busy = f", {len(probe['builds'])} build(s) running" if probe["builds"] else ""
        print(f"        load {probe['load']}{busy}")
    report.note("citadel and the NixOS hosts aren't checked; deploy them by hand")


def check_dependabot(report: Report) -> None:
    report.section("Dependabot")
    prs = run_json(["gh", "pr", "list", "--state", "open", "--author", "app/dependabot", "--json", "number,title"])
    if prs is None:
        report.cannot_tell("could not list PRs")
    elif prs:
        for pr in prs:
            report.flag(f"PR #{pr['number']}: {pr['title']}")
    else:
        report.ok("no open PRs")

    flake_prs = run_json(["gh", "pr", "list", "--state", "open", "--head", "update_flake_lock_action", "--json", "number"])
    if flake_prs is None:
        report.cannot_tell("could not list flake lock PRs")
    for pr in flake_prs or []:
        report.flag(f"flake lock PR #{pr['number']}: read its bot verdict")

    query = (
        '{repository(owner:"GregHilston",name:"toolbox")'
        "{dependencyGraphManifests{totalCount}}}"
    )
    graph = run_json([
        "gh", "api", "graphql", "-H", "Accept: application/vnd.github.hawkgirl-preview+json", "-f", f"query={query}",
    ])
    manifests = graph["data"]["repository"]["dependencyGraphManifests"]["totalCount"] if graph else None
    if manifests is None:
        report.cannot_tell("could not read the dependency graph")
    elif not manifests:
        report.flag("dependency graph sees 0 manifests, so alerts can't fire")
    else:
        report.ok(f"dependency graph sees {manifests} manifests")

    alerts = run_json(["gh", "api", f"repos/{OWNER_REPO}/dependabot/alerts?state=open&per_page=100"])
    if alerts is None:
        report.cannot_tell("could not read alerts")
    elif manifests:
        report.verdict(bool(alerts), f"{len(alerts)} open alerts")
    else:
        report.cannot_tell(f"{len(alerts)} open alerts, which proves nothing without a dependency graph")

    settings = run_json(["gh", "api", f"repos/{OWNER_REPO}/automated-security-fixes"])
    if settings is None:
        report.cannot_tell("could not read the security updates setting")
    else:
        report.verdict(not security_updates_on(settings), f"security updates: {settings}")


def check_audits(report: Report) -> None:
    report.section("npm audit")
    listed = run(["git", "ls-files", "*package-lock.json"])
    if not listed:
        report.cannot_tell("could not list lockfiles")
    for lock in (listed or "").split():
        where = str(Path(lock).parent)
        # npm audit exits 1 when it finds anything, so run() can't be used.
        try:
            done = subprocess.run(
                ["npm", "audit", "--package-lock-only", "--json"],
                cwd=REPO / where, capture_output=True, text=True, timeout=90,
            )
            audit = json.loads(done.stdout)
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            report.cannot_tell(f"{where}: audit failed")
            continue
        if audit_failed(audit):
            report.cannot_tell(f"{where}: audit failed: {audit.get('message', 'no metadata')[:80]}")
        elif audit_needs_attention(audit):
            report.flag(audit_line(where, audit))
        elif audit["metadata"]["vulnerabilities"].get("total"):
            report.note(audit_line(where, audit))
        else:
            report.ok(audit_line(where, audit))


def check_bundled_pi(report: Report) -> None:
    report.section("Homebrew pi")
    installed = run(["pi", "--version"])
    latest = npm_latest("@earendil-works/pi-coding-agent")
    if installed is None or latest is None:
        report.cannot_tell("could not compare pi versions")
    else:
        report.verdict(installed.strip() != latest, f"pi {installed.strip()} here, {latest} on npm; Homebrew may lag npm")
    if shutil.which("brew"):
        files = run(["brew", "list", "pi-coding-agent"]) or ""
        undici = [f for f in files.splitlines() if f.endswith("node_modules/undici/package.json")]
        if undici:
            print(f"        bundled undici {json.loads(Path(undici[0]).read_text())['version']}: a lockfile bump won't change it")


def check_versions(report: Report, lock: dict) -> None:
    report.section("Versions")
    age = lock_age_days(lock, time.time())
    report.verdict(age > STALE_LOCK_DAYS, f"nixpkgs lock is {age} days old")

    nix = re.findall(r'ccstatuslineVersion = "([^"]+)"', (REPO / "nixos/modules/programs/tui/claude.nix").read_text())
    just = re.findall(r'ccstatusline_version="([^"]+)"', (REPO / "justfile").read_text())
    settings = json.loads((REPO / "dot/ccstatusline/.config/ccstatusline/settings.json").read_text())
    pins = {*nix, *just, settings["installation"]["installedVersion"]}
    latest = npm_latest("ccstatusline")
    if latest is None or not nix or not just:
        report.cannot_tell("could not read ccstatusline's pins and latest version")
    else:
        report.verdict(pin_is_behind(pins, latest), f"ccstatusline pins {sorted(pins)}, latest {latest}")

    difit = re.findall(r'DIFIT_VERSION:-([^}]+)\}', (REPO / "bin/difit.sh").read_text())
    latest = npm_latest("difit")
    if latest is None or not difit:
        report.cannot_tell("could not compare difit versions")
    else:
        report.verdict(pin_is_behind(set(difit), latest), f"difit pin {difit[0]}, latest {latest}")

    workflows = "\n".join(path.read_text() for path in (REPO / ".github/workflows").glob("*.yml"))
    tracking = branch_tracking_actions(workflows)
    report.verdict(bool(tracking), f"actions tracking a branch: {', '.join(tracking) or 'none'}")


def check_ci(report: Report) -> None:
    report.section("CI on main")
    runs = run_json([
        "gh", "run", "list", "--branch", "main", "--limit", "30", "--json", "workflowName,status,conclusion,event",
    ])
    if runs is None:
        report.cannot_tell("could not list runs")
        return
    newest = newest_runs(runs)
    if "Tests" not in newest:
        report.cannot_tell("no Tests run in the last 30")
    for name, entry in sorted(newest.items()):
        if entry["status"] != "completed":
            report.cannot_tell(f"{name}: still {entry['status']} ({entry['event']})")
        else:
            report.verdict(entry["conclusion"] != "success", f"{name}: {entry['conclusion']} ({entry['event']})")


def main() -> int:
    report = Report()
    try:
        lock = json.loads((REPO / "nixos/flake.lock").read_text())
    except (OSError, ValueError) as err:
        print(f"could not read nixos/flake.lock: {err}", file=sys.stderr)
        return 2
    guarded(report, check_hosts, lock)
    guarded(report, check_dependabot)
    guarded(report, check_audits)
    guarded(report, check_bundled_pi)
    guarded(report, check_versions, lock)
    guarded(report, check_ci)
    print(f"\n{report.attention} to look at, {report.unknown} could not tell")
    return exit_code(report.attention, report.unknown)


if __name__ == "__main__":
    sys.exit(main())
