"""
Shared plumbing for the cross-engine harness.

The scripts one directory up are oMLX-only: they hardcode `127.0.0.1:8000` and read
the oMLX API key. These ones must drive *any* OpenAI-compatible server (oMLX on 8000,
MTPLX on 18080, whatever comes next) with the SAME measurement code, because the whole
point of an engine comparison is that only the engine differs.

So: reuse `bench.py`'s prompt families and `stream_once()` verbatim, and rebind its
module-level BASE/KEY per run. That keeps one definition of "how we measure decode"
instead of a second copy that can silently drift from the numbers in
docs/local-llm-benchmarks.md.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_BENCH = os.path.dirname(_HERE)

# bench.py calls load_key() at import time and sys.exit()s if no oMLX key is present.
# A non-oMLX arm legitimately has no oMLX key, so satisfy the import and let the caller
# pass the real key (or a dummy) via --key.
os.environ.setdefault("OMLX_API_KEY", "placeholder")
sys.path.insert(0, _BENCH)

import bench  # noqa: E402  (path must be set first)


def bind(base: str, key: str):
    """Point the shared harness at one endpoint. Returns the bench module."""
    bench.BASE = base.rstrip("/")
    bench.KEY = key
    return bench


def load_omlx_key() -> str:
    """oMLX key from $OMLX_API_KEY or bench/omlx_key (gitignored). '' if absent."""
    key = os.environ.get("OMLX_API_KEY", "").strip()
    if key and key != "placeholder":
        return key
    try:
        with open(os.path.join(_BENCH, "omlx_key")) as fh:
            return fh.read().strip()
    except FileNotFoundError:
        return ""


# The sampler every arm runs, on every engine: the official Qwen3.8 contract.
# reasoning_effort is sent BOTH as a top-level field and inside chat_template_kwargs
# because oMLX and MTPLX each accept both, and sending one only would silently leave
# one engine at its template default (xhigh, which does not terminate -- see
# docs/local-llm-benchmarks.md).
QWEN38_EXTRA = {
    "top_p": 0.95,
    "top_k": 20,
    "reasoning_effort": "medium",
    "chat_template_kwargs": {"reasoning_effort": "medium"},
}
QWEN38_TEMPERATURE = 1.0
