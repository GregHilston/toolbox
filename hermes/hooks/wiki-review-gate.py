#!/usr/bin/env python3
"""Refuse librarian writes to the LLM wiki that no human approved.

The llm-wiki-review skill asks the model to stop for review. Its own
QUALIFICATION.md calls that "not deterministic enforcement", qualified on a
frontier model only; the librarian runs local Qwen. An instruction to a small
model is not a gate. This is.

Wired as a pre_tool_call hook on write_file and patch. The rules:

  outside the wiki   blocked
  raw/**             create only; sources are immutable
  Review/**          anything except setting `decision: approve` -- only Greg
                     does that, in Obsidian, or the bot can approve itself --
                     or touching a rejected/applied proposal, which the bot
                     once reopened by overwriting
  index.md, log.md   always; navigation, not knowledge
  everything else    only with a Review/ proposal whose `target` is this path,
                     `decision: approve`, and `status` not yet `applied`

Known hole: `terminal` and `execute_code` can still write files. This stops
the file tools, which is the path the skill uses.
"""
import datetime
import json
import os
import re
import sys
from pathlib import Path

WIKI = Path(os.environ.get("LLM_WIKI_ROOT") or Path.home() / "Git/notes/wiki").expanduser().resolve()
LOG = Path(os.environ.get("WIKI_GATE_LOG") or Path.home() / ".hermes/logs/wiki-review-gate.log")
ALWAYS = {"index.md", "log.md"}
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---", re.S)


def block(reason):
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a") as f:
            f.write(f"[{datetime.datetime.now(datetime.timezone.utc):%FT%TZ}] blocked: {reason.splitlines()[0]}\n")
    except OSError:
        pass
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def field(text, key):
    m = FRONTMATTER.match(text or "")
    if not m:
        return None
    v = re.search(rf"^{key}:[ \t]*(.*?)[ \t]*$", m.group(1), re.M)
    return v.group(1).strip("'\"") if v else None


def after_write(tool, args, path):
    if tool == "write_file":
        return args.get("content", "")
    old, new = args.get("old_string"), args.get("new_string")
    current = path.read_text() if path.exists() else ""
    if old is None or new is None or old not in current:
        block(f"patch on {path.name} refused: the review gate cannot tell what this patch would do to a proposal. Use write_file with the whole proposal instead.")
    return current.replace(old, new) if args.get("replace_all") else current.replace(old, new, 1)


def approved(rel):
    for p in (WIKI / "Review").glob("**/*.md"):
        text = p.read_text(errors="replace")
        if field(text, "target") == rel and field(text, "decision") == "approve" and field(text, "status") != "applied":
            return True
    return False


try:
    payload = json.load(sys.stdin)
    tool = payload["tool_name"]
    args = payload.get("tool_input") or {}
    raw_path = args["path"]
except Exception:
    block("the wiki review gate could not read the tool call payload. This is a harness fault, not your fault: report it rather than working around it.")

if tool not in ("write_file", "patch"):
    sys.exit(0)

# Not payload["cwd"]: that is the gateway's. File tools resolve against terminal.cwd.
path = Path(WIKI, os.path.expanduser(raw_path)).resolve()
if not path.is_relative_to(WIKI):
    block(f"{raw_path} is outside the wiki ({WIKI}). The librarian writes only inside the wiki.")
rel = path.relative_to(WIKI).as_posix()
top = rel.split("/")[0]

if top == "raw":
    if tool == "write_file" and not path.exists():
        sys.exit(0)
    block(f"{rel} is a raw source, and raw sources are immutable. Capture a new source under a new file name; put corrections in a wiki page proposal.")

if top == "Review":
    current = path.read_text(errors="replace") if path.exists() else ""
    if field(current, "status") in ("applied", "rejected"):
        block(f"{rel} is closed ({field(current, 'status')}), and closed proposals are the audit trail. Write a new proposal file instead.")
    now = field(current, "decision")
    if field(after_write(tool, args, path), "decision") == "approve" and now != "approve":
        block(f"{rel}: only Greg approves a proposal, by setting its `decision` property to approve in Obsidian. Tell him the proposal is ready and stop. Recording reject, defer or revise is fine.")
    sys.exit(0)

if rel in ALWAYS or approved(rel):
    sys.exit(0)

block(f"{rel} is a compiled wiki page and no approved proposal targets it. Write a proposal to Review/ with `target: {rel}` and `decision: pending`, then stop for Greg's review.")
