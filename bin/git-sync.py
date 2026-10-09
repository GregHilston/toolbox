#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Relay this branch's unpushed commits through another host, which pushes them.

For a machine whose git identity must not reach the remote (citadel's work
account): the commits travel as patches over one ssh call, so one password
prompt and no key needed. The far host applies them with `git am -3` in a
throwaway worktree off origin, re-authors them with its own identity (author
date becomes now), and pushes. Its own checkout is only fast-forwarded, and
only when on main and clean. Then this checkout resets main to what was pushed.

    git sync                     via dungeon on the LAN, else dungeonts
    git sync --host moriats -y   via one host, no confirmation

Nothing local changes until the pushed commit is confirmed on origin.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import shlex
import socket
import subprocess
import sys
import threading
from pathlib import Path

# Runs on the far host under bash 3.2. Only the pushed sha goes to stdout.
REMOTE_SCRIPT = r"""
set -euo pipefail
exec 3>&1 1>&2
repo=$1 branch=$2
patches=$(mktemp)
wt=$(mktemp -d)
trap 'git worktree remove --force "$wt" 2>/dev/null || rm -rf "$wt"; rm -f "$patches"' EXIT
cat > "$patches"
cd "$HOME/$repo" 2>/dev/null || { echo "no repo at ~/$repo on $(hostname -s)" >&2; exit 10; }
git fetch -q origin "$branch"
git worktree add -q --detach "$wt" "origin/$branch"
hooks=$(git rev-parse --path-format=absolute --git-common-dir)/hooks
cd "$wt"
if ! git am -q -3 "$patches"; then
  git am --abort
  echo "patches conflict with origin/$branch; nothing was pushed" >&2
  exit 12
fi
# Re-authoring is not a new commit; skip commit hooks.
git rebase -q --exec 'git commit -q --no-verify --amend --no-edit --reset-author' "origin/$branch"
# Worktrees miss relative hooksPath; see nixos/CLAUDE.md.
if ! git -c core.hooksPath="$hooks" push -q origin "HEAD:$branch"; then
  echo "push from $(hostname -s) failed; nothing was pushed" >&2
  exit 13
fi
git rev-parse HEAD >&3
# Fast-forward the far checkout only when safe.
cd "$HOME/$repo"
if [ "$(git rev-parse --abbrev-ref HEAD)" = "$branch" ] \
  && [ -z "$(git status --porcelain --untracked-files=no)" ] \
  && git merge-base --is-ancestor HEAD "origin/$branch" \
  && git merge -q --ff-only "origin/$branch"; then
  echo "updated ~/$repo on $(hostname -s) to origin/$branch" >&2
else
  echo "left ~/$repo on $(hostname -s) as it was; pull there when ready" >&2
fi
"""

TAILNET = ipaddress.ip_network("100.64.0.0/10")
SSH_HINTS = {
    "Permission denied": "wrong password (or run `ssh-copy-id {host}` to skip it)",
    "Host key verification failed": "run `ssh {host}` once to accept its key",
    "timed out": "{host} did not answer; is it awake and on Tailscale?",
    "No route to host": "no route to {host}; is Tailscale up?",
    "Network is unreachable": "no network; is Tailscale up?",
    "Could not resolve": "{host} is not a known host; check ~/.ssh/config",
    "Connection refused": "{host} is up but not running sshd (Remote Login)",
}


class RelayError(Exception):
    pass


def git(*args: str) -> str:
    out = subprocess.run(["git", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise RelayError(f"git {' '.join(args)}: {out.stderr.strip()}")
    return out.stdout


def git_ok(*args: str) -> bool:
    return subprocess.run(["git", *args], capture_output=True).returncode == 0


def tailnet_problem(status: dict, ip: str) -> str | None:
    """Why `ip` is unreachable over Tailscale, if it is."""
    state = status.get("BackendState")
    if state == "NeedsLogin":
        return "Tailscale is logged out; log in, then rerun"
    if state != "Running":
        return f"Tailscale is not connected ({state}); connect it, then rerun"
    for peer in (status.get("Peer") or {}).values():
        if ip in peer.get("TailscaleIPs", []):
            if not peer.get("Online"):
                seen = peer.get("LastSeen", "unknown")
                return f"{peer.get('HostName', ip)} is offline on the tailnet (last seen {seen})"
            return None
    return f"{ip} is not a device on this tailnet"


def ssh_hostname(host: str) -> str:
    """Resolve an ssh alias the way ssh will."""
    out = subprocess.run(["ssh", "-G", host], capture_output=True, text=True)
    for line in out.stdout.splitlines():
        key, _, value = line.partition(" ")
        if key == "hostname":
            return value
    return host


def reachable(host: str, timeout: float = 2.0) -> bool:
    """Whether sshd answers, without logging in."""
    out = subprocess.run(["ssh", "-G", host], capture_output=True, text=True)
    conf = dict(line.partition(" ")[::2] for line in out.stdout.splitlines())
    try:
        with socket.create_connection((conf.get("hostname", host), int(conf.get("port", 22))), timeout):
            return True
    except (OSError, ValueError):
        return False


def pick_host(hosts: list[str]) -> str:
    """First reachable host; the last one otherwise."""
    for host in hosts[:-1]:
        if reachable(host):
            return host
        print(f"git-sync: {host} did not answer, trying the next host", file=sys.stderr)
    return hosts[-1]


def check_tailnet(host: str) -> None:
    """Fail early, and plainly, when the tailnet is the problem."""
    ip = ssh_hostname(host)
    try:
        if ipaddress.ip_address(ip) not in TAILNET:
            return
    except ValueError:
        return  # a name, not a tailnet address
    cmd = shlex.split(os.environ.get("RELAY_TAILSCALE", "tailscale status --json"))
    try:
        out = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        print(f"git-sync: no tailscale CLI, so trying {host} unchecked", file=sys.stderr)
        return
    try:
        status = json.loads(out.stdout)
    except json.JSONDecodeError:
        raise RelayError(f"Tailscale is not running; start it and connect, then rerun ({out.stderr.strip()})") from None
    problem = tailnet_problem(status, ip)
    if problem:
        raise RelayError(problem)


def ssh_failure(host: str, stderr: str) -> str:
    """Turn ssh's own failure into a next step."""
    for needle, hint in SSH_HINTS.items():
        if needle in stderr:
            return f"could not ssh to {host}: {hint.format(host=host)}"
    return f"could not ssh to {host}: {stderr.strip() or 'no output'}"


def ssh_command(host: str, repo: str, branch: str) -> list[str]:
    remote = "bash -c " + shlex.join([REMOTE_SCRIPT, "relay", repo, branch])
    prefix = shlex.split(os.environ.get("RELAY_SSH", "ssh -o ConnectTimeout=10"))
    return [*prefix, host, remote]


def run_remote(argv: list[str], patches: bytes) -> tuple[int, str, str]:
    """Stream stderr live, keep a copy for hints."""
    proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def feed() -> None:
        try:
            proc.stdin.write(patches)
            proc.stdin.close()
        except BrokenPipeError:
            pass

    threading.Thread(target=feed, daemon=True).start()
    err = []
    for raw in proc.stderr:
        line = raw.decode(errors="replace")
        sys.stderr.write(line)
        err.append(line)
    out = proc.stdout.read().decode()
    return proc.wait(), out, "".join(err)


def default_repo(root: Path) -> str:
    """Same home-relative path on both hosts."""
    try:
        return str(root.relative_to(Path.home()))
    except ValueError:
        raise RelayError(f"{root} is outside $HOME; pass --repo") from None


def check_commits(base: str, shas: list[str]) -> None:
    """Refuse what patches cannot carry faithfully."""
    if git("rev-list", "--merges", f"{base}..HEAD").strip():
        raise RelayError("merge commits in the range; rebase onto origin first")
    empty = [s[:7] for s in shas if git_ok("diff", "--quiet", f"{s}^", s)]
    if empty:
        raise RelayError(f"empty commits {', '.join(empty)}; drop them first")
    email = subprocess.run(["git", "config", "user.email"], capture_output=True, text=True).stdout.strip()
    if email and email.lower() in git("log", "--format=%B", f"{base}..HEAD").lower():
        raise RelayError(f"{email} appears in a commit message; reword it first")


def confirm() -> bool:
    try:
        return input("Proceed? [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


def finish_here(branch: str, current: str, base: str, pushed: str) -> None:
    git("fetch", "-q", "origin")
    if not git_ok("merge-base", "--is-ancestor", pushed, base):
        raise RelayError(f"{pushed[:7]} is not on {base} yet")
    git("checkout", "-q", branch)
    git("reset", "-q", "--hard", base)
    if current != branch:
        git("branch", "-q", "-D", current)
        print(f"Deleted {current}; its commits are on {base} now.")


def relay(hosts: list[str], repo: str | None, branch: str, assume_yes: bool) -> int:
    root = Path(git("rev-parse", "--show-toplevel").strip())
    os.chdir(root)
    repo = repo or default_repo(root)
    if git("status", "--porcelain", "--untracked-files=no").strip():
        raise RelayError("uncommitted changes here; commit them first")
    current = git("rev-parse", "--abbrev-ref", "HEAD").strip()
    if current == "HEAD":
        raise RelayError("detached HEAD; check out a branch first")

    host = pick_host(hosts)
    check_tailnet(host)
    git("fetch", "-q", "origin")
    base = f"origin/{branch}"
    shas = git("rev-list", "--reverse", f"{base}..HEAD").split()
    if not shas:
        print(f"Nothing to relay: HEAD has no commits beyond {base}.")
        return 0
    if current != branch and git_ok("rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"):
        if set(git("rev-list", f"{base}..{branch}").split()) - set(shas):
            raise RelayError(f"local {branch} has commits not on {current}; relay from {branch}")
    check_commits(base, shas)

    print(f"Relaying {len(shas)} commit(s) from {current} via {host}:~/{repo} to {base}:")
    print(git("log", "--format=  %h %s", f"{base}..HEAD"), end="")
    if not assume_yes and not confirm():
        print("Aborted.")
        return 1

    patches = git("format-patch", "--stdout", f"{base}..HEAD").encode()
    code, out, err = run_remote(ssh_command(host, repo, branch), patches)
    if code == 255:
        raise RelayError(ssh_failure(host, err))
    if code != 0:
        raise RelayError(f"relay on {host} failed (exit {code}); this checkout is untouched")
    pushed = out.strip().splitlines()[-1] if out.strip() else ""
    if not pushed:
        raise RelayError(f"{host} reported no pushed commit; check {base} before rerunning")

    try:
        finish_here(branch, current, base, pushed)
    except RelayError as err:
        raise RelayError(
            f"pushed {pushed[:7]} to {base}, but finishing here failed: {err}\n"
            f"  finish with: git fetch origin && git checkout {branch} && git reset --hard {base}"
        ) from None
    print(f"Done: {branch} is at {git('log', '-1', '--format=%h %s', base).strip()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="dungeon,dungeonts", help="ssh hosts to try in order (default: dungeon,dungeonts)")
    parser.add_argument("--repo", help="repo path under the far host's $HOME (default: same as here)")
    parser.add_argument("--branch", default="main", help="branch to land on (default: main)")
    parser.add_argument("-y", "--yes", action="store_true", help="skip the confirmation")
    args = parser.parse_args(argv)
    try:
        return relay(args.host.split(","), args.repo, args.branch, args.yes)
    except RelayError as err:
        print(f"git-sync: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
