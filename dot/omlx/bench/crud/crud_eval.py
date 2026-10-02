#!/usr/bin/env python3
"""
One-table CRUD app eval: the model writes a SQLite + React app as files, this
script installs, runs and grades it, then feeds failures back as hint turns.

The model never runs anything itself. Every hint sent is the grader's own
failure report, saved verbatim in results/<arm>/hints-round-N.md.

    python3 crud_eval.py <model> <arm> [--rounds 2] [--no-restart] [--host dungeon]

--host sends generation to that host's oMLX and reads its swap over ssh;
grading still runs here. It never restarts a remote server.
"""
import argparse, json, os, re, shutil, signal, subprocess, sys, threading, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from _key import load_key

BASE = "http://127.0.0.1:8000"
HOST = None
KEY = load_key()
API_PORT, UI_PORT = 3001, 5199
API = f"http://localhost:{API_PORT}"
GRADER_DIR = os.path.expanduser("~/.cache/crud-eval-grader")
GRADER_NODE = os.path.join(GRADER_DIR, "node_modules", "playwright-core")
SETTINGS = os.path.join(os.path.dirname(os.path.dirname(HERE)), ".omlx", "model_settings.json")

FILE_RE = re.compile(r"^#{2,4}\s+`?([\w./-]+?)`?\s*\n```[^\n]*\n(.*?)\n```", re.S | re.M)


def restart_omlx():
    pids = subprocess.run(["lsof", "-ti", "tcp:8000", "-sTCP:LISTEN"], capture_output=True, text=True).stdout.split()
    for p in pids:
        os.kill(int(p), signal.SIGTERM)
    subprocess.run(["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/org.nixos.omlx"], check=True)
    while True:
        try:
            urllib.request.urlopen(f"{BASE}/health", timeout=2)
            break
        except Exception:
            time.sleep(2)
    time.sleep(15)


def ensure_grader():
    """Install the browser grader once; a broken one would grade every UI check 0."""
    if not os.path.isdir(GRADER_NODE):
        os.makedirs(GRADER_DIR, exist_ok=True)
        subprocess.run("npm init -y >/dev/null && npm install --silent playwright-core@1.63.0", cwd=GRADER_DIR, shell=True, check=True)
    subprocess.run("npx --no-install playwright-core install chromium-headless-shell", cwd=GRADER_DIR, shell=True, check=True,
                   capture_output=True)
    probe = "require('playwright-core').chromium.launch().then(b => b.close())"
    if subprocess.run(["node", "-e", probe], cwd=GRADER_DIR, capture_output=True).returncode:
        sys.exit(f"the browser grader in {GRADER_DIR} cannot launch Chromium; fix that before measuring")


def model_settings(model):
    """The served settings; arms differ in budget, so record them."""
    entry = json.load(open(SETTINGS))["models"].get(model.split(":")[0], {})
    return {k: v for k, v in entry.items() if not k.startswith(("_", "description"))}


def swap_used_mb():
    cmd = ["sysctl", "-n", "vm.swapusage"]
    out = subprocess.run(["ssh", HOST, *cmd] if HOST else cmd, capture_output=True, text=True).stdout
    return float(re.search(r"used = ([\d.]+)M", out).group(1))


class SwapWatch(threading.Thread):
    """Peak swap while generating; any growth fails a model."""
    def __init__(self):
        super().__init__(daemon=True)
        self.start_mb = swap_used_mb()
        self.peak_mb = self.start_mb
        self.stop = False

    def run(self):
        while not self.stop:
            self.peak_mb = max(self.peak_mb, swap_used_mb())
            time.sleep(3)


def chat(model, messages, max_tokens, extra):
    body = {"model": model, "messages": messages, "max_tokens": max_tokens, "stream": True,
            "stream_options": {"include_usage": True}, **extra}
    req = urllib.request.Request(f"{BASE}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    t0 = time.perf_counter()
    ttft, content, reasoning, usage, finish = None, [], [], None, None
    with urllib.request.urlopen(req, timeout=7200) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data:") or line == "data: [DONE]":
                continue
            ev = json.loads(line[5:])
            usage = ev.get("usage") or usage
            for ch in ev.get("choices", []):
                d = ch.get("delta", {})
                piece = d.get("content") or ""
                think = d.get("reasoning_content") or d.get("reasoning") or ""
                if (piece or think) and ttft is None:
                    ttft = time.perf_counter() - t0
                content.append(piece)
                reasoning.append(think)
                finish = ch.get("finish_reason") or finish
    wall = time.perf_counter() - t0
    return {"content": "".join(content), "reasoning": "".join(reasoning), "usage": usage,
            "finish": finish, "wall_s": round(wall, 1), "ttft_s": round(ttft or 0, 1)}


def write_files(text, root):
    files = FILE_RE.findall(text)
    written = []
    for path, body in files:
        if path.startswith("/") or ".." in path.split("/") or "node_modules" in path:
            continue
        if path.endswith(("package-lock.json", "data.db")):
            continue
        full = os.path.join(root, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as fh:
            fh.write(body + "\n")
        written.append(path)
    return written


# This PATH puts GCC's g++ first; node-gyp needs clang.
BUILD_ENV = {**os.environ, "CC": "clang", "CXX": "clang++"}


def sh(cmd, cwd, timeout=600):
    if not os.path.isdir(cwd):
        return 1, f"there is no {os.path.basename(cwd)}/ directory"
    p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout, env=BUILD_ENV)
    return p.returncode, (p.stdout + p.stderr)[-3000:]


def start(cmd, cwd, env, log):
    fh = open(log, "w")
    if not os.path.isdir(cwd):
        fh.write(f"there is no {os.path.basename(cwd)}/ directory\n")
        cwd = "/"
        cmd = "exit 1"
    return subprocess.Popen(cmd, cwd=cwd, shell=True, env={**os.environ, **env}, stdout=fh,
                            stderr=subprocess.STDOUT, start_new_session=True)


def stop(proc):
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(10)
    except Exception:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except Exception:
            pass


def free_ports():
    for port in (API_PORT, UI_PORT):
        for p in subprocess.run(["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"], capture_output=True, text=True).stdout.split():
            os.kill(int(p), signal.SIGKILL)


def http(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            status, raw = r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return 0, None
    try:
        return status, json.loads(raw) if raw.strip() else None
    except ValueError:
        return status, None


def wait_up(url, secs=40):
    for _ in range(secs * 2):
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except urllib.error.HTTPError:
            return True
        except Exception:
            time.sleep(0.5)
    return False


def as_list(b):
    if isinstance(b, dict):
        b = b.get("books") or b.get("data")
    return [x for x in b if isinstance(x, dict)] if isinstance(b, list) else []


def as_book(b):
    if isinstance(b, dict):
        inner = b.get("book") or b.get("data")
        return inner if isinstance(inner, dict) else b
    return {}


def grade(root, logdir):
    procs = []
    try:
        return _grade(root, logdir, procs)
    finally:
        for p in procs:
            stop(p)
        free_ports()


def _grade(root, logdir, procs):
    checks, notes = {}, {}
    server, client = os.path.join(root, "server"), os.path.join(root, "client")
    free_ports()
    if os.path.exists(os.path.join(server, "data.db")):
        os.remove(os.path.join(server, "data.db"))

    rc, out = sh("npm install --no-audit --no-fund", server)
    notes["server npm install"] = out if rc else ""
    srv = start("npm start", server, {"PORT": str(API_PORT)}, f"{logdir}/server.log")
    procs.append(srv)
    up = rc == 0 and wait_up(API + "/api/books")
    checks["server_starts"] = up
    if up:
        s, b = http("GET", "/api/books")
        listed = b.get("books") or b.get("data") if isinstance(b, dict) else b
        checks["list"] = s == 200 and isinstance(listed, list)
        s, b = http("POST", "/api/books", {"title": "Dune", "author": "Herbert", "year": 1965, "read": False})
        bid = as_book(b).get("id")
        checks["create"] = s in (200, 201) and bid is not None
        s, b = http("GET", f"/api/books/{bid}")
        checks["get_one"] = s == 200 and as_book(b).get("title") == "Dune"
        s, b = http("PUT", f"/api/books/{bid}", {"title": "Dune Messiah", "author": "Herbert", "year": 1969, "read": True})
        s2, b2 = http("GET", f"/api/books/{bid}")
        checks["update"] = s in (200, 204) and as_book(b2).get("title") == "Dune Messiah" and bool(as_book(b2).get("read"))
        s1, _ = http("POST", "/api/books", {"title": "", "author": "x"})
        s2, _ = http("POST", "/api/books", {"title": "x"})
        s3, _ = http("PUT", f"/api/books/{bid}", {"title": "x", "author": ""})
        checks["validation_400"] = (s1, s2, s3) == (400, 400, 400)
        notes["validation statuses (empty title POST, missing author POST, empty author PUT)"] = str((s1, s2, s3))
        s4, _ = http("GET", "/api/books/987654")
        s5, _ = http("PUT", "/api/books/987654", {"title": "x", "author": "y"})
        s6, _ = http("DELETE", "/api/books/987654")
        checks["not_found_404"] = (s4, s5, s6) == (404, 404, 404)
        notes["unknown-id statuses (GET, PUT, DELETE)"] = str((s4, s5, s6))
        s, _ = http("DELETE", f"/api/books/{bid}")
        s2, _ = http("GET", f"/api/books/{bid}")
        checks["delete"] = s in (200, 204) and s2 == 404
        http("POST", "/api/books", {"title": "Persist", "author": "P"})
        stop(srv)
        srv = start("npm start", server, {"PORT": str(API_PORT)}, f"{logdir}/server2.log")
        procs.append(srv)
        s, b = http("GET", "/api/books") if wait_up(API + "/api/books") else (0, None)
        checks["persists_restart"] = any(x.get("title") == "Persist" for x in as_list(b))
        if not s:
            notes["server log after restart"] = open(f"{logdir}/server2.log").read()[-2500:]
        checks["db_file"] = os.path.exists(os.path.join(server, "data.db"))
    else:
        for k in ("list", "create", "get_one", "update", "validation_400", "not_found_404", "delete", "persists_restart", "db_file"):
            checks[k] = False
        notes["server log"] = open(f"{logdir}/server.log").read()[-2500:]

    rc, out = sh("npm install --no-audit --no-fund", client)
    notes["client npm install"] = out if rc else ""
    rc, out = sh("npm run build", client) if rc == 0 else (1, "install failed")
    checks["client_build"] = rc == 0
    notes["client build"] = out if rc else ""

    ui = {}
    if checks["server_starts"] and os.path.exists(os.path.join(client, "package.json")):
        dev = start(f"npm run dev -- --port {UI_PORT} --strictPort", client, {}, f"{logdir}/vite.log")
        procs.append(dev)
        if wait_up(f"http://localhost:{UI_PORT}/", 60):
            p = subprocess.run(["node", os.path.join(HERE, "ui_test.js"), f"http://localhost:{UI_PORT}/", API, logdir],
                               capture_output=True, text=True, timeout=180, env={**os.environ, "PW_CORE": GRADER_NODE})
            try:
                ui = json.loads(p.stdout.strip().splitlines()[-1])
            except Exception:
                notes["ui test"] = (p.stdout + p.stderr)[-2000:]
        else:
            notes["vite log"] = open(f"{logdir}/vite.log").read()[-2000:]
    for k in ("list", "create", "toggle", "edit", "delete"):
        checks[f"ui_{k}"] = bool(ui.get(k))
    if ui.get("errors"):
        notes["ui errors"] = "\n".join(ui["errors"])
    return checks, notes


def feedback(checks, notes):
    failed = [k for k, v in checks.items() if not v]
    lines = ["I installed and ran your app. These checks failed: " + ", ".join(failed) + "."]
    for k, v in notes.items():
        if v:
            lines.append(f"\n{k}:\n```\n{v.strip()[-2000:]}\n```")
    lines.append("\nFix the problems. Output only the files you change, in full, in the same format as before.")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("arm")
    ap.add_argument("--rounds", type=int, default=2, help="hint rounds after the first attempt")
    ap.add_argument("--max-tokens", type=int, default=32768)
    ap.add_argument("--extra", default="{}", help="JSON merged into the request body")
    ap.add_argument("--no-restart", action="store_true")
    ap.add_argument("--host", help="remote oMLX host, e.g. dungeon")
    a = ap.parse_args()
    global BASE, HOST
    if a.host:
        BASE, HOST = f"http://{a.host}:8000", a.host

    root = f"/tmp/crud-eval/{a.arm}/app"
    out = os.path.join(HERE, "results", a.arm)
    shutil.rmtree(f"/tmp/crud-eval/{a.arm}", ignore_errors=True)
    os.makedirs(root)
    os.makedirs(out, exist_ok=True)
    ensure_grader()
    if not (a.no_restart or a.host):
        restart_omlx()

    messages = [{"role": "user", "content": open(os.path.join(HERE, "PROMPT.md")).read()}]
    summary = {"model": a.model, "arm": a.arm, "host": a.host or "moria", "extra": json.loads(a.extra),
               "settings": model_settings(a.model), "rounds": []}
    for rnd in range(a.rounds + 1):
        watch = SwapWatch()
        watch.start()
        r = chat(a.model, messages, a.max_tokens, json.loads(a.extra))
        watch.stop = True
        files = write_files(r["content"], root)
        with open(f"{out}/response-round-{rnd}.md", "w") as fh:
            fh.write(r["content"])
        logdir = f"{out}/round-{rnd}"
        os.makedirs(logdir, exist_ok=True)
        checks, notes = grade(root, logdir)
        u = r["usage"] or {}
        ct = u.get("completion_tokens", 0)
        rec = {"round": rnd, "score": sum(checks.values()), "of": len(checks), "checks": checks,
               "files": files, "finish": r["finish"], "completion_tokens": ct,
               "reasoning_tokens": (u.get("completion_tokens_details") or {}).get("reasoning_tokens"),
               "prompt_tokens": u.get("prompt_tokens"), "wall_s": r["wall_s"], "ttft_s": r["ttft_s"],
               "decode_tps": round(ct / max(r["wall_s"] - r["ttft_s"], 0.1), 1),
               "swap_start_mb": watch.start_mb, "swap_peak_mb": watch.peak_mb,
               "swap_growth_mb": round(watch.peak_mb - watch.start_mb, 1)}
        summary["rounds"].append(rec)
        print(json.dumps({k: v for k, v in rec.items() if k not in ("checks", "files")}), flush=True)
        print("  failed:", [k for k, v in checks.items() if not v], flush=True)
        with open(f"{out}/summary.json", "w") as fh:
            json.dump(summary, fh, indent=1)
        if all(checks.values()) or rnd == a.rounds:
            break
        hint = feedback(checks, notes)
        with open(f"{out}/hints-round-{rnd + 1}.md", "w") as fh:
            fh.write(hint)
        messages += [{"role": "assistant", "content": r["content"]}, {"role": "user", "content": hint}]


if __name__ == "__main__":
    main()
