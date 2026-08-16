#!/usr/bin/env python3
"""
Executable coding eval against oMLX models.

For each task: prompt the model, extract the fenced python block, exec it in a
subprocess, run the task's assertions, record pass/fail. Objective, no judging.
"""
import json, os, re, subprocess, sys, tempfile, time, urllib.request, argparse, statistics
from tasks import TASKS

BASE = "http://127.0.0.1:8000/v1"
HERE = os.path.dirname(os.path.abspath(__file__))
KEY = open(os.path.join(HERE, "omlx_key")).read().strip()

FENCE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.S)


def extract_code(text):
    blocks = FENCE.findall(text or "")
    if blocks:
        # concatenate all blocks: models sometimes split helper + main
        return "\n\n".join(b.strip() for b in blocks)
    return (text or "").strip()


def call(model, prompt, max_tokens, temperature, extra=None, timeout=2400):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if extra:
        body.update(extra)
    req = urllib.request.Request(
        f"{BASE}/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    content, reasoning, usage, finish = [], [], None, None
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for raw in r:
            line = raw.decode("utf-8").strip()
            if not line.startswith("data:"):
                continue
            p = line[5:].strip()
            if p == "[DONE]":
                break
            try:
                ev = json.loads(p)
            except json.JSONDecodeError:
                continue
            if ev.get("usage"):
                usage = ev["usage"]
            for ch in ev.get("choices", []):
                if ch.get("finish_reason"):
                    finish = ch["finish_reason"]
                d = ch.get("delta", {}) or {}
                if d.get("content"):
                    content.append(d["content"])
                if d.get("reasoning_content"):
                    reasoning.append(d["reasoning_content"])
    return {
        "content": "".join(content),
        "reasoning_chars": len("".join(reasoning)),
        "wall": time.perf_counter() - t0,
        "usage": usage or {},
        # 'length' means the token budget ran out -- with reasoning_effort defaulting to
        # xhigh, a model can burn the whole budget thinking and never emit the answer.
        # That is a truncation, not a wrong answer, and must be reported separately.
        "finish": finish,
    }


RUNNER = """\
import sys
{code}

# ---- tests ----
{test}
print("__PASS__")
"""


def run_code(code, test, timeout=25):
    src = RUNNER.format(code=code, test=test)
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
        fh.write(src)
        path = fh.name
    try:
        p = subprocess.run(
            [sys.executable, path], capture_output=True, text=True, timeout=timeout
        )
        ok = "__PASS__" in p.stdout
        err = (p.stderr or "").strip().splitlines()
        return ok, ("" if ok else (err[-1] if err else "no output")[:300])
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    finally:
        os.unlink(path)


def eval_model(model, max_tokens, temperature, extra=None, reps=1):
    print(f"\n{'='*74}\nEVAL {model} (temp={temperature}, extra={extra})\n{'='*74}", flush=True)
    rows = []
    for t in TASKS:
        for rep in range(reps):
            try:
                r = call(model, t["prompt"], max_tokens, temperature, extra)
            except Exception as e:
                print(f"  {t['name']:24s} rep{rep} CALL-FAIL {type(e).__name__}: {e}", flush=True)
                rows.append({"task": t["name"], "rep": rep, "ok": False, "err": f"call:{e}"})
                continue
            code = extract_code(r["content"])
            ok, err = run_code(code, t["test"])
            ct = r["usage"].get("completion_tokens", 0)
            rows.append(
                {
                    "task": t["name"], "rep": rep, "ok": ok, "err": err,
                    "completion_tokens": ct,
                    "reasoning_chars": r["reasoning_chars"],
                    "wall": round(r["wall"], 1),
                    "tps": round(ct / r["wall"], 2) if r["wall"] else 0,
                    "finish": r["finish"],
                }
            )
            trunc = " [TRUNCATED]" if r["finish"] == "length" else ""
            print(
                f"  {t['name']:24s} rep{rep} {'PASS' if ok else 'FAIL'} "
                f"| {ct:5d} tok | {r['wall']:6.1f}s | {ct/r['wall'] if r['wall'] else 0:5.1f} t/s"
                f"{trunc}" + ("" if ok else f" | {err[:80]}"),
                flush=True,
            )
    n = len(rows)
    passed = sum(1 for x in rows if x["ok"])
    truncated = sum(1 for x in rows if x.get("finish") == "length")
    toks = sum(x["completion_tokens"] for x in rows)
    print(
        f"  ==> {model}: {passed}/{n} = {100*passed/n:.1f}%"
        f"   (truncated: {truncated}, total tokens spent: {toks})",
        flush=True,
    )
    return {"model": model, "passed": passed, "total": n,
            "truncated": truncated, "tokens": toks, "rows": rows}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("models", nargs="+")
    ap.add_argument("--max-tokens", type=int, default=8000)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--out", default=None)
    ap.add_argument("--extra", default=None, help="JSON merged into request body")
    a = ap.parse_args()
    extra = json.loads(a.extra) if a.extra else None

    all_res = {}
    for m in a.models:
        all_res[m] = eval_model(m, a.max_tokens, a.temperature, extra, a.reps)
        if a.out:
            json.dump(all_res, open(a.out, "w"), indent=2)

    print(f"\n{'='*74}\nSUMMARY\n{'='*74}")
    for m, r in all_res.items():
        print(f"  {m:34s} {r['passed']}/{r['total']}  ({100*r['passed']/r['total']:.1f}%)"
              f"  truncated={r.get('truncated',0)}  tokens={r.get('tokens',0)}")
