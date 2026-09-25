#!/usr/bin/env python3
"""Race builder models on three small cards through one-shot Hermes runs.

    python3 run.py [--reps 2] [--deadline HH:MM] [--arms moe,dense,...]
    python3 run.py --report <run-dir>

Each run copies a task's seed into a fresh git repo, gives the prompt to the
`abtest` profile (the builder's config, minus Kanban hooks, with its shell
started in that repo), then scores it with hidden tests the agent never saw.
Kanban is left out on purpose: its gate and goal loop dominate wall-clock.
"""
import argparse, datetime as dt, hashlib, json, os, re, shutil, sqlite3, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS = ["county", "intervals", "todo"]
# Rejected arms: see notes ref-hermes-run-log.
ARMS = {
    "moe":         ("Qwen3.6-35B-A3B-4bit-DWQ", None),
    "dense":       ("Qwen3.8-27B-4bit", None),
    "deepseek":    ("deepseek-flash", "deepseek"),
    "q9b":         ("Qwen3.5-9B-MLX-4bit", None),
    # Qwen builds, then Claude checks the work against the spec and sends it back.
    "moe+claude":  ("Qwen3.6-35B-A3B-4bit-DWQ", "claude-review"),
    "moe+deepseek": ("Qwen3.6-35B-A3B-4bit-DWQ", "deepseek-review"),
}
REVIEWS = 2
REVIEW_PROMPT = """You are reviewing another agent's work in this repository. Do not edit any file.
The task it was given is below. Check whether the work is really complete and correct:
read the code, run `uv run pytest`, and check each requirement and edge case in the task
against the code, running small checks of your own where useful.

Reply with exactly `VERDICT: DONE` or `VERDICT: NOT DONE` on the first line. If not done,
follow it with a short list of the specific defects, each one concrete enough to fix.

--- TASK ---
"""
BUDGET = 900  # seconds, enforced by Hermes; the kill below is the backstop
STATE = Path.home() / ".hermes/profiles/abtest/state.db"


def sh(cmd, cwd, timeout=300):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def digest(root, rel):
    h = hashlib.sha256()
    for p in sorted((root / rel).rglob("*") if (root / rel).is_dir() else [root / rel]):
        if p.is_file() and "__pycache__" not in p.parts:
            h.update(p.name.encode()); h.update(p.read_bytes())
    return h.hexdigest()


def pytest_counts(out):
    got = {k: int(v) for v, k in re.findall(r"(\d+) (passed|failed|error|errors)", out)}
    return got.get("passed", 0), got.get("failed", 0) + got.get("error", 0) + got.get("errors", 0)


def usage(session_id):
    ids = [i for i in (session_id if isinstance(session_id, list) else [session_id]) if i]
    if not ids or not STATE.exists():
        return {}
    con = sqlite3.connect(STATE)
    row = con.execute(
        "SELECT SUM(api_call_count), SUM(input_tokens), SUM(output_tokens), SUM(cache_read_tokens),"
        " SUM(reasoning_tokens), SUM(estimated_cost_usd) FROM session_model_usage"
        f" WHERE session_id IN ({','.join('?' * len(ids))})", ids).fetchone()
    con.close()
    keys = ["calls", "tok_in", "tok_out", "tok_cached", "tok_reason", "cost_usd"]
    return {k: (v or 0) for k, v in zip(keys, row)}


def omlx_isolate(keep):
    """Unload every model but `keep`: resident neighbours cut decode speed ~10x."""
    import http.cookiejar, urllib.request
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    base = "http://127.0.0.1:8000/admin/api"
    login = urllib.request.Request(f"{base}/login", json.dumps({"api_key": os.environ["OMLX_API_KEY"]}).encode(),
                                   {"Content-Type": "application/json"})
    op.open(login, timeout=30)
    # Picks up models downloaded mid-sweep. It unloads everything, so only between runs.
    op.open(urllib.request.Request(f"{base}/reload", b"", method="POST"), timeout=300)
    models = json.load(op.open(f"{base}/models", timeout=30))
    for m in models.get("models", models):
        mid = m.get("id") or m.get("model_id")
        if mid != keep and (m.get("loaded") or m.get("is_loaded") or m.get("status") == "loaded"):
            op.open(urllib.request.Request(f"{base}/models/{mid}/unload", b"", method="POST"), timeout=120)


def run_one(run_dir, task, arm, rep):
    model, provider = ARMS[arm]
    omlx_isolate(model if provider in (None, "claude-review", "deepseek-review") else None)
    src = HERE / "tasks" / task
    ws = run_dir / f"{task}-{arm}-r{rep}"
    shutil.rmtree(ws, ignore_errors=True)  # a run killed mid-way is redone
    shutil.copytree(src / "seed", ws)
    for c in (["git", "init", "-q"], ["git", "add", "-A"], ["git", "commit", "-qm", "seed"]):
        subprocess.run(c, cwd=ws, check=True)
    guarded = "tests" if task == "intervals" else "pyproject.toml"
    before = digest(ws, guarded)

    spec = (src / "prompt.md").read_text()
    t0 = time.time()
    extra = {}
    if provider in ("claude-review", "deepseek-review"):
        prompt, sids, code, cost = spec, [], 0, 0.0
        for rnd in range(REVIEWS + 1):
            code, sid = hermes(ws, model, None, prompt, BUDGET - (time.time() - t0), f"build{rnd}")
            sids.append(sid)
            if rnd == REVIEWS or time.time() - t0 > BUDGET:
                break
            verdict, notes, c = (claude_review if provider == "claude-review" else deepseek_review)(ws, spec, rnd)
            cost += c
            if verdict:
                break
            prompt = spec + "\n\nA reviewer checked your work and found these defects. Fix them:\n" + notes
        extra = dict(rounds=len(sids), review_cost_usd=round(cost, 4))
        sid = sids
    else:
        code, sid = hermes(ws, model, provider, spec, BUDGET, "build0")
    wall = time.time() - t0

    vis_code, vis_out = sh(["uv", "run", "--quiet", "pytest", "-q", "-p", "no:cacheprovider"], ws)
    vis_pass, vis_fail = pytest_counts(vis_out)

    # Hidden tests run on a copy, so the agent's tree is left as it was.
    chk = run_dir / ".check" / ws.name
    shutil.copytree(ws, chk, ignore=shutil.ignore_patterns(".venv", "__pycache__"))
    (chk / "tests").mkdir(exist_ok=True)
    shutil.copy(src / "hidden_test.py", chk / "tests" / "test_hidden_zz.py")
    _, hid_out = sh(["uv", "run", "--quiet", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_hidden_zz.py"], chk)
    hid_total = (src / "hidden_test.py").read_text().count("\ndef test_")
    hid_pass, _ = pytest_counts(hid_out)
    shutil.rmtree(chk, ignore_errors=True)

    rec = dict(task=task, arm=arm, model=model, rep=rep, wall_s=round(wall), exit=code,
               timed_out=code == 124 or wall >= BUDGET, visible_green=vis_code == 0 and vis_pass > 0,
               visible_pass=vis_pass, visible_fail=vis_fail, hidden_pass=hid_pass, hidden_total=hid_total,
               tampered=digest(ws, guarded) != before, session=sid, finished=dt.datetime.now().isoformat(timespec="seconds"))
    rec.update(usage(sid))
    rec.update(extra)
    return rec


def hermes(ws, model, provider, prompt, budget, tag):
    budget = max(int(budget), 60)
    cmd = ["hermes", "-p", "abtest", "chat", "-Q", "--yolo", "--ignore-rules", "--source", "abtest",
           "--max-turns", "60", "--run-budget", str(budget), "-m", model, "-q", prompt]
    if provider:
        cmd += ["--provider", provider]
    env = dict(os.environ, AB_CWD=str(ws))
    try:
        p = subprocess.run(cmd, cwd=ws, env=env, capture_output=True, text=True, timeout=budget + 120)
        out, code = p.stdout + p.stderr, p.returncode
    except subprocess.TimeoutExpired as e:
        out, code = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or ""), 124
    (ws / f".ab-{tag}.log").write_text(out)
    return code, (re.findall(r"session_id:\s*(\S+)", out) or [None])[-1]


def deepseek_review(ws, spec, rnd):
    code, sid = hermes(ws, "deepseek-flash", "deepseek", REVIEW_PROMPT + spec, 600, f"review{rnd}")
    text = (ws / f".ab-review{rnd}.log").read_text()
    body = text.split("VERDICT:", 1)
    verdict = len(body) == 2 and body[1].strip().upper().startswith("DONE")
    return verdict, "VERDICT:" + body[1] if len(body) == 2 else text[-3000:], usage(sid).get("cost_usd", 0)


def claude_review(ws, spec, rnd):
    cmd = ["claude", "-p", REVIEW_PROMPT + spec, "--model", "sonnet", "--output-format", "json",
           "--allowedTools", "Read", "Grep", "Glob", "Bash(uv run:*)", "Bash(python3:*)", "Bash(cat:*)", "Bash(ls:*)",
           "--disallowedTools", "Edit", "Write", "MultiEdit", "NotebookEdit"]
    try:
        p = subprocess.run(cmd, cwd=ws, capture_output=True, text=True, timeout=600)
        d = json.loads(p.stdout)
    except Exception as e:
        (ws / f".ab-review{rnd}.log").write_text(f"review failed: {e}")
        return True, "", 0.0
    text = d.get("result") or ""
    (ws / f".ab-review{rnd}.log").write_text(text)
    return text.strip().upper().startswith("VERDICT: DONE"), text, float(d.get("total_cost_usd") or 0)


def report(run_dir):
    rows = [json.loads(l) for l in (run_dir / "results.jsonl").read_text().splitlines() if l.strip()]
    lines = [f"# Builder quick A/B — {run_dir.name}", "", f"{len(rows)} runs. Hidden tests: 5 + 7 + 5 per rep.", "",
             "| Arm | Runs | Solved | Hidden tests | Green suite | False done | Mean min | Timeouts | Tampered | Out tok/run | Out tok/s | Calls/run | Cost |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for arm in ARMS:
        r = [x for x in rows if x["arm"] == arm]
        if not r:
            continue
        hp, ht = sum(x["hidden_pass"] for x in r), sum(x["hidden_total"] for x in r)
        solved = sum(x["hidden_pass"] == x["hidden_total"] for x in r)
        wall = sum(x["wall_s"] for x in r)
        out = sum(x.get("tok_out", 0) for x in r)
        lines.append(
            f"| {arm} | {len(r)} | {solved}/{len(r)} | {hp}/{ht} ({100*hp/ht:.0f}%) | "
            f"{sum(x['visible_green'] for x in r)}/{len(r)} | "
            f"{sum(x['visible_green'] and x['hidden_pass'] < x['hidden_total'] for x in r)} | {wall/len(r)/60:.1f} | "
            f"{sum(x['timed_out'] for x in r)} | {sum(x['tampered'] for x in r)} | "
            f"{out/len(r):,.0f} | {out/max(wall,1):.0f} | {sum(x.get('calls',0) for x in r)/len(r):.0f} | "
            f"${sum(x.get('cost_usd',0) + x.get('review_cost_usd',0) for x in r):.3f} |")
    lines += ["", "Per task: hidden tests passed, minutes.", "", "| Arm | " + " | ".join(TASKS) + " |",
              "|---|" + "---|" * len(TASKS)]
    for arm in ARMS:
        cells = []
        for t in TASKS:
            r = [x for x in rows if x["arm"] == arm and x["task"] == t]
            cells.append(", ".join(f"{x['hidden_pass']}/{x['hidden_total']} {x['wall_s']/60:.1f}m" for x in r) or "—")
        if any(c != "—" for c in cells):
            lines.append(f"| {arm} | " + " | ".join(cells) + " |")
    text = "\n".join(lines) + "\n"
    (run_dir / "report.md").write_text(text)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--deadline", help="HH:MM local; start no run after it")
    ap.add_argument("--report", type=Path)
    ap.add_argument("--run-dir", type=Path)
    a = ap.parse_args()
    if a.report:
        print(report(a.report)); return
    run_dir = a.run_dir or Path.home() / "Git/agent-runs/quick-ab" / dt.datetime.now().strftime("%Y%m%d-%H%M")
    run_dir.mkdir(parents=True, exist_ok=True)
    stop = None
    if a.deadline:
        h, m = map(int, a.deadline.split(":"))
        stop = dt.datetime.now().replace(hour=h, minute=m, second=0)
        if stop < dt.datetime.now():
            stop += dt.timedelta(days=1)
    done = set()
    res = run_dir / "results.jsonl"
    if res.exists():
        done = {(r["task"], r["arm"], r["rep"]) for r in map(json.loads, res.read_text().splitlines()) if r}
    print(f"run dir: {run_dir}", flush=True)
    models_dir = Path.home() / "Git/toolbox/dot/omlx/.omlx/models"
    ready = lambda arm: ARMS[arm][1] in ("deepseek",) or (models_dir / ARMS[arm][0] / "config.json").exists()
    pending = [(rep, task, arm) for rep in range(1, a.reps + 1) for task in TASKS
               for arm in a.arms.split(",") if (task, arm, rep) not in done]
    while pending:
        if stop and dt.datetime.now() >= stop:
            print("deadline reached", flush=True); break
        nxt = next((p for p in pending if ready(p[2])), None)
        if nxt is None:  # everything left is still downloading
            time.sleep(60); continue
        pending.remove(nxt)
        rep, task, arm = nxt
        rec = run_one(run_dir, task, arm, rep)
        with res.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"{rec['finished']} {task:9} {arm:11} r{rep} {rec['wall_s']/60:5.1f}m "
              f"hidden {rec['hidden_pass']}/{rec['hidden_total']} green={rec['visible_green']} "
              f"out={rec.get('tok_out',0)} timeout={rec['timed_out']}", flush=True)
        report(run_dir)
    print(report(run_dir), flush=True)

if __name__ == "__main__":
    main()
