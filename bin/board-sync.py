#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Copy a repo's issue labels onto a GitHub Projects kanban board.

Labels stay the source of truth, because /prep, to-tickets and overnight-loop.py
all write them and `gh issue list --label` can query them. The board is a view:
this sets each issue's Status from its labels, so never drag cards by hand.
Needs the gh token's `project` scope: `gh auth refresh -s project`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

COLUMNS = [  # name, colour, description; the first matching rule wins
    ("Backlog", "GRAY", "Not yet prepped for an agent"),
    ("Todo", "BLUE", "ready-for-agent or prep:ready"),
    ("In progress", "PURPLE", "overnight:working, the loop is on it"),
    ("Review", "YELLOW", "overnight:done, playtest and merge"),
    ("Blocked", "RED", "overnight:parked or prep:blocked, needs a human"),
    ("Done", "GREEN", "Closed"),
]


def status(state: str, labels: set[str]) -> str:
    if state == "CLOSED":
        return "Done"
    if labels & {"overnight:parked", "prep:blocked"}:
        return "Blocked"
    if "overnight:done" in labels:
        return "Review"
    if "overnight:working" in labels:
        return "In progress"
    if labels & {"ready-for-agent", "prep:ready"}:
        return "Todo"
    return "Backlog"


def gh(*args: str) -> str:
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode:
        sys.exit(f"gh {' '.join(args[:3])} failed: {out.stderr.strip()}")
    return out.stdout


def status_field(owner: str, number: int) -> dict:
    query = """query($o: String!, $n: Int!) { user(login: $o) { projectV2(number: $n) {
        id field(name: "Status") { ... on ProjectV2SingleSelectField { id options { id name } } } } } }"""
    data = json.loads(gh("api", "graphql", "-f", f"o={owner}", "-F", f"n={number}", "-f", f"query={query}"))
    return data["data"]["user"]["projectV2"]["field"]


def create(owner: str, repo: str, title: str) -> int:
    number = int(gh("project", "create", "--owner", owner, "--title", title, "--format", "json", "--jq", ".number"))
    gh("project", "link", str(number), "--owner", owner, "--repo", repo)
    field = status_field(owner, number)
    # Keep Done's id, so the built-in "item closed -> Done" workflow still points at it.
    done = next(o["id"] for o in field["options"] if o["name"] == "Done")
    options = ", ".join(
        f'{{{"id: " + json.dumps(done) + ", " if name == "Done" else ""}name: {json.dumps(name)}, '
        f'color: {colour}, description: {json.dumps(desc)}}}'
        for name, colour, desc in COLUMNS)
    mutation = f'mutation {{ updateProjectV2Field(input: {{fieldId: "{field["id"]}", singleSelectOptions: [{options}]}}) {{ clientMutationId }} }}'
    gh("api", "graphql", "-f", f"query={mutation}")
    print(f"Created project {number}. In its web page, switch the view to Board, grouped by Status.")
    return number


def sync(owner: str, repo: str, number: int, dry_run: bool) -> None:
    issues = json.loads(gh("issue", "list", "-R", repo, "--state", "all", "--limit", "1000",
                           "--json", "number,url,state,labels"))
    items = json.loads(gh("project", "item-list", str(number), "--owner", owner, "--limit", "1000",
                          "--format", "json"))["items"]
    current = {i["content"].get("url"): i.get("status") for i in items if i.get("content")}
    for issue in sorted(issues, key=lambda i: i["number"]):
        want = status(issue["state"], {lab["name"] for lab in issue["labels"]})
        if current.get(issue["url"]) == want:
            continue
        print(f"#{issue['number']}: {current.get(issue['url']) or 'not on board'} -> {want}")
        if dry_run:
            continue
        if issue["url"] not in current:
            gh("project", "item-add", str(number), "--owner", owner, "--url", issue["url"])
        gh("project", "item-edit", str(number), "--owner", owner, "--url", issue["url"],
           "--field", "Status", "--value", want)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--project", type=int, help="the project number; omit with --create")
    p.add_argument("--create", metavar="TITLE", help="create a board for this repo, with the columns, then sync")
    p.add_argument("--dry-run", action="store_true", help="print the moves without making them")
    args = p.parse_args()
    repo = json.loads(gh("repo", "view", "--json", "nameWithOwner"))["nameWithOwner"]
    owner = repo.split("/")[0]
    number = create(owner, repo, args.create) if args.create else args.project
    if number is None:
        sys.exit("give --project N, or --create TITLE to make the board")
    sync(owner, repo, number, args.dry_run)


if __name__ == "__main__":
    main()
