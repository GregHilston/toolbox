#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Rank Jira tickets in a given order, replacing backlog drag-and-drop.

The Agile rank API moves the listed tickets as one block directly after the
first one, keeping list order. Only their order relative to each other changes;
the first ticket stays where it is. The script reads the order back to verify.

Auth: JIRA_EMAIL and JIRA_API_TOKEN from the environment, else resolved at run
time with `op read` from JIRA_EMAIL_REF and JIRA_API_TOKEN_REF. Those refs live
in the env or nixos/secrets/work.env (`just secrets`), written without the
op:// prefix because `op inject` resolves bare refs too. The token never touches
disk, and 1Password's Touch ID prompt gates every run, so an agent on citadel
can't write to tickets unnoticed. Scoped API tokens only work through the
api.atlassian.com gateway, which is the default base URL here; scopes needed
are read:jira-work (search) and the granular write:issue:jira-software
(rank, per Atlassian's OpenAPI spec; write:jira-work is not enough). For a classic token set
JIRA_BASE_URL=https://mozilla-hub.atlassian.net.
"""

from __future__ import annotations

import argparse
import base64
import functools
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

CLOUD_ID = "d8febd08-c6e9-4c03-9c13-db37c2369ce5"  # mozilla-hub.atlassian.net
DEFAULT_BASE_URL = f"https://api.atlassian.com/ex/jira/{CLOUD_ID}"
SEARCH_PATH = "/rest/api/3/search/jql"
RANK_PATH = "/rest/agile/1.0/issue/rank"
RANK_FIELD = "customfield_10019"  # mozilla-hub's Rank field
MAX_RANKED = 50  # Agile rank API limit per call
TIMEOUT_S = 30
KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]+-\d+$")


class JiraError(Exception):
    """A failed Jira call, with method, path and status."""


def to_keys(tickets: list[str], project: str) -> list[str]:
    """Turn `5326` or `mntor-5326` into `MNTOR-5326`.

    Raises ValueError on a malformed key or a duplicate.
    """
    keys = [t.upper() if "-" in t else f"{project.upper()}-{t}" for t in tickets]
    bad = [k for k in keys if not KEY_RE.match(k)]
    if bad:
        raise ValueError(f"bad ticket keys: {', '.join(bad)}")
    dupes = sorted({k for k in keys if keys.count(k) > 1})
    if dupes:
        raise ValueError(f"duplicate tickets: {', '.join(dupes)}")
    return keys


def work_env_path() -> Path:
    """Locate the `just secrets` work file."""
    toolbox = Path(os.environ.get("TOOLBOX_HOME", Path.home() / "Git" / "toolbox"))
    return toolbox / "nixos" / "secrets" / "work.env"


def work_env_value(name: str) -> str | None:
    """Read one plain value from work.env."""
    try:
        lines = work_env_path().read_text().splitlines()
    except OSError:
        return None
    for line in lines:
        if m := re.fullmatch(rf"(?:export )?{name}=(['\"]?)(.+)\1", line.strip()):
            return m.group(2)
    return None


def op_read(ref: str) -> str | None:
    """Resolve a 1Password ref; None on failure."""
    try:
        out = subprocess.run(["op", "read", ref], capture_output=True, text=True,
                             check=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"op read failed for {ref}: {e}", file=sys.stderr)
        return None
    return out.stdout.strip() or None


def as_op_ref(ref: str) -> str:
    """Add the op:// prefix if missing."""
    return ref if ref.startswith("op://") else f"op://{ref}"


@functools.cache
def secret(name: str) -> str | None:
    """Get a value from env, else its 1Password ref."""
    if value := os.environ.get(name):
        return value
    ref = os.environ.get(f"{name}_REF") or work_env_value(f"{name}_REF")
    return op_read(as_op_ref(ref)) if ref else None


def auth_header() -> str:
    """Build the basic auth header from secrets."""
    creds = f"{secret('JIRA_EMAIL')}:{secret('JIRA_API_TOKEN')}".encode()
    return "Basic " + base64.b64encode(creds).decode()


def error_hint(status: int, path: str) -> str:
    """Suggest a likely cause for common failures."""
    if status == 401:
        return " (check token, scopes: write:issue:jira-software, JIRA_BASE_URL)"
    if status == 400 and path == SEARCH_PATH:
        return " (a ticket key may not exist)"
    return ""


def send_json(method: str, path: str, body: dict) -> tuple[int, dict]:
    """Send a JSON request to Jira, return status and body.

    Raises JiraError on HTTP or network failure.
    """
    req = urllib.request.Request(
        os.environ.get("JIRA_BASE_URL", DEFAULT_BASE_URL) + path,
        data=json.dumps(body).encode(),
        method=method,
        headers={
            "Authorization": auth_header(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        raise JiraError(f"{method} {path} {e.code}{error_hint(e.code, path)}: {detail}") from e
    except urllib.error.URLError as e:
        raise JiraError(f"{method} {path} unreachable: {e.reason}") from e


def current_order(keys: list[str]) -> list[str]:
    """Return the tickets sorted by their stored rank.

    Sorts on the LexoRank value itself: `ORDER BY rank` uses the
    search index, which lags writes by seconds to minutes.
    """
    jql = f"key in ({', '.join(keys)})"
    _, data = send_json("POST", SEARCH_PATH,
                        {"jql": jql, "fields": [RANK_FIELD], "maxResults": len(keys)})
    issues = data.get("issues", [])
    return [i["key"] for i in sorted(issues, key=lambda i: i["fields"][RANK_FIELD])]


def failed_entries(data: dict) -> list[str]:
    """List `KEY (status)` for each failed rank entry."""
    return [f"{e.get('issueKey')} ({e.get('status')}: {e.get('errors')})"
            for e in data.get("entries", []) if e.get("status") != 200]


def rank(keys: list[str]) -> None:
    """Place keys[1:] directly after keys[0], in list order.

    Raises JiraError if any ticket fails to move.
    """
    status, data = send_json("PUT", RANK_PATH, {"issues": keys[1:], "rankAfterIssue": keys[0]})
    failed = failed_entries(data) if status == 207 else []
    if failed:
        raise JiraError(f"PUT {RANK_PATH} 207: rank failed for {', '.join(failed)}")


def parse_args(argv: list[str] | None) -> tuple[argparse.ArgumentParser, argparse.Namespace]:
    """Define and parse the command line."""
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("tickets", nargs="+", help="ticket numbers or keys, highest rank first")
    p.add_argument("--project", default="MNTOR", help="key prefix for bare numbers")
    p.add_argument("--dry-run", action="store_true", help="show current vs wanted order only")
    return p, p.parse_args(argv)


def valid_keys(p: argparse.ArgumentParser, args: argparse.Namespace) -> list[str]:
    """Validate input and env; exit 2 on bad input."""
    try:
        keys = to_keys(args.tickets, args.project)
    except ValueError as e:
        p.error(str(e))
    if not 2 <= len(keys) <= MAX_RANKED + 1:
        p.error(f"give 2 to {MAX_RANKED + 1} tickets")
    for var in ("JIRA_EMAIL", "JIRA_API_TOKEN"):
        if not secret(var):
            p.error(f"{var} missing; set it or {var}_REF")
    return keys


def run(keys: list[str], dry_run: bool) -> int:
    """Show orders, rank if needed, verify; return exit code."""
    before = current_order(keys)
    print("current:", " ".join(before))
    print("wanted: ", " ".join(keys))
    missing = sorted(set(keys) - set(before))
    if missing:
        print(f"not found: {', '.join(missing)}", file=sys.stderr)
        return 1
    if before == keys:
        print("already in order")
        return 0
    if dry_run:
        return 0
    rank(keys)
    after = current_order(keys)
    print("now:    ", " ".join(after))
    if after != keys:
        print("order mismatch after rank", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point; return the process exit code."""
    p, args = parse_args(argv)
    keys = valid_keys(p, args)
    try:
        return run(keys, args.dry_run)
    except (JiraError, KeyError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
