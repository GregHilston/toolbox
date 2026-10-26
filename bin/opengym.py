#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Read and change the routines in Greg's openGym, the way the phone app syncs them.

    opengym.py pair <CODE>          trade a pairing code for a token (one time)
    opengym.py show [ROUTINE]       routines with their exercises, or one routine in full
    opengym.py search <TEXT>        exercise library ids whose name holds TEXT
    opengym.py push [ROUTINE ...]   make the server's routines match the plan file
    opengym.py delete <ROUTINE>     remove a routine, by name or id

The plan file, home-lab's opengym/gym-routine.opengym.json, is the source of truth; `push`
replaces a routine of the same name in place, keeping its id so history and schedule still
point at it, and adds one that is missing. Writes go through PUT /api/data with baseRev and
no `stamped`, so the server stamps them and a phone syncing later cannot undo them
(upstream api/openapi.yaml, api/sync-stamps.js). The token is a paired phone's bearer
token: GET /api/me renews it, so every run saves the renewed one.
"""
from __future__ import annotations

import json
import re
import secrets
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SERVER = "https://gym.grehg2.xyz"
TOKEN = Path.home() / ".config" / "opengym" / "token"
HOME_LAB = Path.home() / "Git" / "home-lab"
PLAN = HOME_LAB / "opengym" / "gym-routine.opengym.json"
COMPOSE = HOME_LAB / "docker-compose.yaml"
LIBRARY = "https://raw.githubusercontent.com/DuarteSantos8/openGym/v{}/api/coach/core/library-data.js"


def call(method: str, path: str, token: str | None = None, body: dict | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(SERVER + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")
    except urllib.error.URLError as e:
        sys.exit(f"opengym: cannot reach {SERVER} ({e.reason}); is Tailscale up?")


def token() -> str:
    if not TOKEN.is_file():
        sys.exit(f"opengym: no token at {TOKEN}. In a browser at {SERVER}: Settings → Account → "
                 "Pair the mobile app, then run `opengym.py pair <CODE>`")
    tok = TOKEN.read_text().strip()
    status, me = call("GET", "/api/me", tok)
    if status == 401:
        sys.exit(f"opengym: token rejected (expired or signed out); pair again with `opengym.py pair <CODE>`")
    if me.get("token"):
        save_token(me["token"])
        tok = me["token"]
    return tok


def save_token(tok: str) -> None:
    TOKEN.parent.mkdir(parents=True, exist_ok=True)
    TOKEN.touch(mode=0o600)
    TOKEN.write_text(tok + "\n")


def library() -> dict[str, str]:
    """Library id → name, at the version home-lab runs, so ids match the server's."""
    m = re.search(r"opengym-api:(\S+)", COMPOSE.read_text())
    if not m:
        sys.exit(f"opengym: no opengym-api image tag in {COMPOSE}")
    with urllib.request.urlopen(LIBRARY.format(m.group(1)), timeout=30) as r:
        src = r.read().decode()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    return {x["id"]: x["n"] for x in rows}


def new_id() -> str:
    """Shaped like the app's own ids: base-36 time, then random."""
    n, digits = int(time.time() * 1000), ""
    while n:
        n, d = divmod(n, 36)
        digits = "0123456789abcdefghijklmnopqrstuvwxyz"[d] + digits
    return digits + secrets.token_hex(3)[:5]


def find(state: dict, key: str) -> dict:
    hits = [r for r in state.get("routines") or [] if key in (r.get("id"), r.get("name"))]
    if len(hits) != 1:
        names = ", ".join(f"{r.get('name')} ({r.get('id')})" for r in state.get("routines") or [])
        why = "no routine" if not hits else f"{len(hits)} routines"
        sys.exit(f"opengym: {why} named {key!r}; delete the extra by id. Routines: {names}")
    return hits[0]


def apply_plan(state: dict, plan: dict, names: list[str], lib: dict[str, str]) -> list[str]:
    """Put the plan's routines (all, or those named) into `state`. Returns what changed."""
    if plan.get("unit") != state.get("unit"):
        sys.exit(f"opengym: plan is in {plan.get('unit')}, the app in {state.get('unit')}; convert the plan first")
    routines = [r for r in plan["routines"] if not names or r["name"] in names]
    if missing := set(names) - {r["name"] for r in routines}:
        sys.exit(f"opengym: not in the plan file: {', '.join(sorted(missing))}")
    state.setdefault("routines", [])
    state.setdefault("customEx", [])
    custom = {c["id"]: c for c in plan.get("customEx") or []}
    ids: dict[str, str] = {}
    done = []
    for r in routines:
        for e in r["ex"]:
            if e["id"] in custom:
                ids[e["id"]] = custom_id(state, custom[e["id"]])
            elif e["id"] not in lib:
                sys.exit(f"opengym: {r['name']}: exercise id {e['id']} is neither in the library "
                         "nor in the plan's customEx; find one with `opengym.py search`")
        ex = [{**e, "id": ids.get(e["id"], e["id"])} for e in r["ex"]]
        same = [x for x in state["routines"] if x.get("name") == r["name"]]
        if len(same) > 1:
            find(state, r["name"])
        if same:
            same[0].update(name=r["name"], emoji=r.get("emoji"), ex=ex)
            done.append(f"replaced {r['name']}")
        else:
            state["routines"].append({"id": new_id(), "name": r["name"], "emoji": r.get("emoji"), "ex": ex})
            done.append(f"added {r['name']}")
    return done


def custom_id(state: dict, c: dict) -> str:
    """The app's id for a plan's custom exercise, adding it the way an import would."""
    for x in state["customEx"]:
        if (x.get("n") or "").lower() == c["n"].lower() and x.get("bp") == c.get("bp"):
            return x["id"]
    x = {**c, "id": new_id(), "custom": True}
    if c.get("secondaries"):
        x["sm"] = c["secondaries"]
    state["customEx"].append(x)
    return x["id"]


def label(state: dict, lib: dict[str, str], ex_id: str) -> str:
    custom = {c["id"]: c["n"] for c in state.get("customEx") or []}
    return custom.get(ex_id) or lib.get(ex_id) or f"? {ex_id}"


def dose(e: dict) -> str:
    side = " per side" if e.get("side") else ""
    if "min" in e:
        return f"{e['min']} min"
    if e.get("mode") == "time":
        return f"{e.get('sets', 1)} x {e.get('sec')}s{side}"
    reps = e.get("reps", 10)
    return f"{e.get('sets', 1)} x {reps // 2 if side else reps}{side}"


def put(tok: str, state: dict, rev: int) -> None:
    status, body = call("PUT", "/api/data", tok, {"state": state, "baseRev": rev})
    if status == 409:
        sys.exit("opengym: the app synced while this ran; run the command again")
    if status != 200:
        sys.exit(f"opengym: server refused the write ({status}): {body}")


def main(argv: list[str]) -> None:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip().split("\n\n")[1])
        return
    cmd, args = argv[0], argv[1:]
    if cmd == "pair" and len(args) == 1:
        status, body = call("POST", "/api/pair/redeem", body={"code": args[0]})
        if status != 200 or not body.get("token"):
            sys.exit(f"opengym: pairing refused ({status}): {body.get('error')}; codes last 5 minutes")
        save_token(body["token"])
        print(f"paired; token saved to {TOKEN}")
        return
    if cmd == "search" and args:
        text = " ".join(args).lower()
        for i, n in library().items():
            if text in n.lower():
                print(f"{i}\t{n}")
        return
    if cmd not in ("show", "push", "delete") or (cmd == "delete" and len(args) != 1):
        sys.exit(f"opengym: bad command {' '.join(argv)!r}; see opengym.py -h")
    tok = token()
    status, data = call("GET", "/api/data", tok)
    if status != 200 or not data.get("state"):
        sys.exit(f"opengym: could not read the app's data ({status}): {data.get('error')}")
    state, rev, lib = data["state"], data["rev"], library()
    if cmd == "show":
        for r in [find(state, args[0])] if args else state.get("routines") or []:
            print(f"{r.get('name')} ({r.get('id')})")
            for e in r.get("ex") or []:
                print(f"  {label(state, lib, e['id'])} [{e['id']}]: {dose(e)}")
                if args and e.get("note"):
                    print(f"      {e['note']}")
    elif cmd == "push":
        done = apply_plan(state, json.loads(PLAN.read_text()), args, lib)
        put(tok, state, rev)
        print("; ".join(done) + ". The phone picks it up on its next sync.")
    else:
        r = find(state, args[0])
        state["routines"].remove(r)
        week = state.get("week") or {}
        for day, val in list(week.items()):
            # A day may hold one id or a list.
            left = [x for x in (val if isinstance(val, list) else [val]) if x != r["id"]]
            if left:
                week[day] = left
            else:
                del week[day]
        put(tok, state, rev)
        print(f"deleted {r['name']} ({r['id']})")


if __name__ == "__main__":
    main(sys.argv[1:])
