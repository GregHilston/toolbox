#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Score a harness run against the rubric fixed before either arm started.

Static checks parse the agent's code; they never import or execute it. Anything
that must actually run is handed to `docker exec` inside that arm's own sandbox,
because agent-authored code is untrusted and does not belong on the host.
"""

from __future__ import annotations

import argparse
import ast
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

IO_LIBRARIES = {
    "httpx", "requests", "urllib", "urllib3", "aiohttp", "socket", "sqlite3",
    "pandas", "polars", "pyarrow", "bs4", "selectolax", "lxml", "pydantic",
    "open", "pathlib",
}


@dataclass
class Score:
    harness: str
    workspace: str
    package_found: str | None = None
    python_files: int = 0
    lines_of_code: int = 0
    test_files: int = 0
    tests_collected: int | None = None
    tests_passed: int | None = None
    tests_failed: int | None = None
    build_exit_code: int | None = None
    domain_purity: bool | None = None
    domain_violations: list[str] = field(default_factory=list)
    dto_containment: bool | None = None
    dto_violations: list[str] = field(default_factory=list)
    ports_are_protocols: bool | None = None
    frozen_domain_types: int = 0
    mappers: int = 0
    mapper_tests: int = 0
    fixtures: int = 0
    raw_cache_files: int = 0
    dataset_files: list[str] = field(default_factory=list)
    dataset_rows: int | None = None
    notes: list[str] = field(default_factory=list)


def find_package(workspace: Path) -> Path | None:
    """The agent chooses its own layout; find the package rather than assume it."""
    for candidate in ("src", "."):
        base = workspace / candidate
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if child.is_dir() and (child / "__init__.py").exists():
                return child
    return None


def iter_py(root: Path):
    for p in sorted(root.rglob("*.py")):
        if any(part in {".venv", "node_modules", "__pycache__", ".git"} for part in p.parts):
            continue
        yield p


def top_level_imports(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


def check_domain_purity(pkg: Path, score: Score) -> None:
    domain = pkg / "domain"
    if not domain.is_dir():
        score.notes.append("no domain/ package")
        score.domain_purity = False
        return
    banned = IO_LIBRARIES - {"open", "pathlib"}
    violations = []
    for path in iter_py(domain):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            violations.append(f"{path.name}: syntax error")
            continue
        hits = top_level_imports(tree) & banned
        if hits:
            violations.append(f"{path.relative_to(pkg)}: {', '.join(sorted(hits))}")
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for dec in node.decorator_list:
                    src = ast.unparse(dec)
                    if "dataclass" in src and "frozen=True" in src:
                        score.frozen_domain_types += 1
    score.domain_violations = violations
    score.domain_purity = not violations


def check_dto_containment(pkg: Path, score: Score) -> None:
    """A DTO that leaks out of its adapter package is the failure this pattern exists to stop."""
    adapters = pkg / "adapters"
    if not adapters.is_dir():
        score.notes.append("no adapters/ package")
        score.dto_containment = False
        return
    dto_modules = {p.parent.name for p in adapters.rglob("dto.py")}
    score.mappers = len(list(adapters.rglob("mapper.py")))
    violations = []
    for path in iter_py(pkg):
        owner = path.parent.name
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and "dto" in node.module:
                source = node.module.split(".")
                for mod in dto_modules:
                    if mod in source and owner != mod:
                        violations.append(f"{path.relative_to(pkg)} imports {node.module}")
    score.dto_violations = violations
    score.dto_containment = not violations


def check_ports(pkg: Path, score: Score) -> None:
    ports = pkg / "ports"
    if not ports.is_dir():
        score.notes.append("no ports/ package")
        score.ports_are_protocols = False
        return
    classes = protocols = 0
    for path in iter_py(ports):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes += 1
                if any("Protocol" in ast.unparse(b) for b in node.bases):
                    protocols += 1
    score.ports_are_protocols = classes > 0 and protocols == classes


def measure_size(workspace: Path, pkg: Path | None, score: Score) -> None:
    root = pkg if pkg else workspace
    files = list(iter_py(root))
    score.python_files = len(files)
    score.lines_of_code = sum(
        len(p.read_text(encoding="utf-8", errors="replace").splitlines()) for p in files
    )
    tests = workspace / "tests"
    if tests.is_dir():
        test_files = list(iter_py(tests))
        score.test_files = len(test_files)
        score.mapper_tests = sum(1 for p in test_files if "mapper" in p.name or "adapter" in str(p))
        fixtures = tests / "fixtures"
        score.fixtures = len(list(fixtures.rglob("*"))) if fixtures.is_dir() else 0
    raw = workspace / "data" / "raw"
    score.raw_cache_files = len([p for p in raw.rglob("*") if p.is_file()]) if raw.is_dir() else 0
    final = workspace / "data" / "final"
    if final.is_dir():
        score.dataset_files = sorted(p.name for p in final.iterdir() if p.is_file())
        for p in final.glob("*.csv"):
            try:
                score.dataset_rows = max(
                    score.dataset_rows or 0,
                    sum(1 for _ in p.open(encoding="utf-8", errors="replace")) - 1,
                )
            except OSError:
                pass


def run_in_container(container: str, workdir: str, command: str, timeout: int = 900):
    """Execute agent-written code only inside the sandbox it was written in."""
    if not shutil.which("docker"):
        return None, "docker not found"
    probe = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", container],
        capture_output=True, text=True,
    )
    if probe.stdout.strip() != "true":
        return None, f"container {container} is not running"
    # The entrypoint exports UV_OFFLINE for the gateway and its workers, but a
    # `docker exec` gets the image environment instead. Without it uv spends ~50s
    # retrying PyPI and then fails, so an offline run scored a working build as
    # exit 1 — the tree was fine, the scoring was not. Mirror the container's own
    # AGENT_OFFLINE rather than taking it as a flag nobody will remember to pass.
    env_flags = []
    offline = subprocess.run(
        ["docker", "inspect", "-f",
         "{{range .Config.Env}}{{println .}}{{end}}", container],
        capture_output=True, text=True,
    )
    if "AGENT_OFFLINE=1" in offline.stdout:
        env_flags = ["-e", "UV_OFFLINE=1"]
    try:
        done = subprocess.run(
            ["docker", "exec", "-w", workdir, *env_flags, container, "bash", "-lc", command],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None, "timed out"
    return done.returncode, (done.stdout + done.stderr)[-4000:]


def parse_pytest(output: str) -> tuple[int | None, int | None, int | None]:
    passed = failed = collected = None
    for line in reversed(output.splitlines()):
        if " passed" in line or " failed" in line or "error" in line.lower():
            import re
            p = re.search(r"(\d+) passed", line)
            f = re.search(r"(\d+) failed", line)
            if p or f:
                passed = int(p.group(1)) if p else 0
                failed = int(f.group(1)) if f else 0
                collected = passed + failed
                break
    return collected, passed, failed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("workspace", help="the arm's workspace directory on the host")
    ap.add_argument("--harness", required=True)
    ap.add_argument("--container", help="running sandbox container, for executing tests")
    ap.add_argument("--container-workdir", default="/instance/workspace")
    ap.add_argument("--build-cmd", default="uv run vt-smb build")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    workspace = Path(args.workspace).expanduser()
    if not workspace.is_dir():
        print(f"no such workspace: {workspace}", file=sys.stderr)
        return 2

    score = Score(harness=args.harness, workspace=str(workspace))
    pkg = find_package(workspace)
    score.package_found = str(pkg.relative_to(workspace)) if pkg else None

    measure_size(workspace, pkg, score)
    if pkg:
        check_domain_purity(pkg, score)
        check_dto_containment(pkg, score)
        check_ports(pkg, score)
    else:
        score.notes.append("no importable package found; static checks skipped")

    if args.container:
        code, out = run_in_container(args.container, args.container_workdir, "uv run pytest -q 2>&1 | tail -20")
        if code is None:
            score.notes.append(f"pytest not run: {out}")
        else:
            score.tests_collected, score.tests_passed, score.tests_failed = parse_pytest(out)
        code, out = run_in_container(args.container, args.container_workdir, f"{args.build_cmd} >/dev/null 2>&1; echo $?")
        if code is not None:
            tail = out.strip().splitlines()
            try:
                score.build_exit_code = int(tail[-1]) if tail else None
            except ValueError:
                score.build_exit_code = None

    if args.json:
        print(json.dumps(asdict(score), indent=2))
        return 0

    d = asdict(score)
    print(f"\n  {'HARNESS':<26} {score.harness}")
    print(f"  {'package':<26} {score.package_found or '— none found —'}")
    print(f"  {'python files / LOC':<26} {score.python_files} / {score.lines_of_code}")
    print(f"  {'test files':<26} {score.test_files}")
    print(f"  {'tests passed / failed':<26} {score.tests_passed} / {score.tests_failed}")
    print(f"  {'build exit code':<26} {score.build_exit_code}")
    print(f"  {'domain/ is pure':<26} {score.domain_purity}  {score.domain_violations or ''}")
    print(f"  {'DTOs contained':<26} {score.dto_containment}  {score.dto_violations or ''}")
    print(f"  {'ports are Protocols':<26} {score.ports_are_protocols}")
    print(f"  {'frozen domain types':<26} {score.frozen_domain_types}")
    print(f"  {'mappers / mapper tests':<26} {score.mappers} / {score.mapper_tests}")
    print(f"  {'recorded fixtures':<26} {score.fixtures}")
    print(f"  {'raw cache files':<26} {score.raw_cache_files}")
    print(f"  {'dataset files':<26} {score.dataset_files or '—'}")
    print(f"  {'dataset rows':<26} {score.dataset_rows}")
    for n in score.notes:
        print(f"  note: {n}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
