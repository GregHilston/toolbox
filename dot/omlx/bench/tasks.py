"""
Original coding tasks with executable unit tests.

Written fresh (not HumanEval/MBPP) to reduce benchmark-contamination risk, and
skewed toward the failure modes that matter for agentic coding: edge cases,
precise spec-following, and stateful/algorithmic reasoning rather than one-liners.

Each task: prompt -> model emits a fenced python block -> we exec it, then run
`test()`. Score = fraction of tasks whose test() completes without raising.
"""

TASKS = [
    {
        "name": "interval_merge_weighted",
        "prompt": """Write a Python function:

    def merge_weighted(intervals: list[tuple[int, int, int]]) -> list[tuple[int, int, int]]:

`intervals` is a list of (start, end, weight) with start < end, half-open [start, end).
Intervals may overlap arbitrarily and are not sorted.

Return the minimal list of non-overlapping half-open intervals covering exactly the
same points, where each output interval carries the SUM of the weights of all input
intervals covering it. Output must be sorted by start. Adjacent output intervals that
share the same weight must be merged into one. Gaps (points covered by no input) must
NOT appear in the output.

Example:
    merge_weighted([(0, 5, 1), (2, 8, 10)]) == [(0, 2, 1), (2, 5, 11), (5, 8, 10)]
    merge_weighted([(0, 2, 3), (2, 4, 3)])  == [(0, 4, 3)]
    merge_weighted([])                      == []

Return ONLY a fenced python code block containing the function.""",
        "test": """
assert merge_weighted([(0,5,1),(2,8,10)]) == [(0,2,1),(2,5,11),(5,8,10)]
assert merge_weighted([(0,2,3),(2,4,3)]) == [(0,4,3)]
assert merge_weighted([]) == []
assert merge_weighted([(0,1,5)]) == [(0,1,5)]
# disjoint with a gap -> gap absent
assert merge_weighted([(0,2,1),(5,7,2)]) == [(0,2,1),(5,7,2)]
# triple overlap
assert merge_weighted([(0,10,1),(2,8,2),(4,6,4)]) == [(0,2,1),(2,4,3),(4,6,7),(6,8,3),(8,10,1)]
# identical intervals stack
assert merge_weighted([(0,3,2),(0,3,2)]) == [(0,3,4)]
# unsorted input
assert merge_weighted([(5,7,2),(0,2,1)]) == [(0,2,1),(5,7,2)]
# merging equal adjacent weights across a boundary
assert merge_weighted([(0,4,1),(4,8,1),(8,12,1)]) == [(0,12,1)]
""",
    },
    {
        "name": "topo_sort_stable",
        "prompt": """Write a Python function:

    def stable_toposort(nodes: list[str], edges: list[tuple[str, str]]) -> list[str] | None:

`nodes` is a list of unique node names in their original declared order.
`edges` is a list of (a, b) meaning "a must come before b".

Return a topological ordering. Among all valid orderings, return the one that is
lexicographically smallest with respect to the ORIGINAL INDEX of each node in `nodes`
(i.e. whenever several nodes are simultaneously available, always emit the one that
appeared earliest in `nodes`). If a cycle makes ordering impossible, return None.

Edges referencing unknown nodes should be ignored. Duplicate edges are allowed.

Return ONLY a fenced python code block containing the function.""",
        "test": """
assert stable_toposort(["a","b","c"], []) == ["a","b","c"]
assert stable_toposort(["c","b","a"], []) == ["c","b","a"]
assert stable_toposort(["a","b","c"], [("c","a")]) == ["b","c","a"]
assert stable_toposort(["a","b"], [("a","b"),("b","a")]) is None
assert stable_toposort([], []) == []
assert stable_toposort(["a","b","c"], [("a","z")]) == ["a","b","c"]
assert stable_toposort(["a","b","c"], [("a","b"),("a","b")]) == ["a","b","c"]
# earliest-declared tie-break under constraint
assert stable_toposort(["x","y","z"], [("z","y")]) == ["x","z","y"]
r = stable_toposort(["d","c","b","a"], [("a","b"),("b","c")])
assert r == ["d","a","b","c"], r
# self-loop is a cycle
assert stable_toposort(["a"], [("a","a")]) is None
""",
    },
    {
        "name": "semver_range",
        "prompt": """Write a Python function:

    def satisfies(version: str, spec: str) -> bool:

Implement a subset of npm-style semver matching. `version` is "MAJOR.MINOR.PATCH"
(all non-negative integers, no pre-release tags).

`spec` is one of:
  - "*"            -> matches any version
  - "1.2.3"        -> exact match
  - "^1.2.3"       -> >=1.2.3 and < the next MAJOR (2.0.0). BUT if major is 0, caret
                      pins the minor: ^0.2.3 means >=0.2.3 and <0.3.0.
                      And ^0.0.3 means >=0.0.3 and <0.0.4.
  - "~1.2.3"       -> >=1.2.3 and <1.3.0 (pins minor)
  - ">=1.2.3", ">1.2.3", "<=1.2.3", "<1.2.3"  -> ordinary comparisons

Comparison is numeric per component (so 1.10.0 > 1.9.0). Whitespace around the spec
should be tolerated. Return True/False.

Return ONLY a fenced python code block containing the function.""",
        "test": """
assert satisfies("1.2.3", "*") is True
assert satisfies("1.2.3", "1.2.3") is True
assert satisfies("1.2.4", "1.2.3") is False
assert satisfies("1.9.0", ">1.10.0") is False
assert satisfies("1.10.0", ">1.9.0") is True
assert satisfies("1.2.3", "^1.2.3") is True
assert satisfies("1.9.9", "^1.2.3") is True
assert satisfies("2.0.0", "^1.2.3") is False
assert satisfies("1.2.2", "^1.2.3") is False
# caret with major 0 pins minor
assert satisfies("0.2.9", "^0.2.3") is True
assert satisfies("0.3.0", "^0.2.3") is False
# caret with major 0 minor 0 pins patch
assert satisfies("0.0.3", "^0.0.3") is True
assert satisfies("0.0.4", "^0.0.3") is False
# tilde
assert satisfies("1.2.9", "~1.2.3") is True
assert satisfies("1.3.0", "~1.2.3") is False
# comparators + whitespace
assert satisfies("1.2.3", "  >=1.2.3 ") is True
assert satisfies("1.2.3", "<=1.2.3") is True
assert satisfies("1.2.3", "<1.2.3") is False
""",
    },
    {
        "name": "lru_ttl_cache",
        "prompt": """Write a Python class:

    class LRUTTLCache:
        def __init__(self, capacity: int, clock): ...
        def put(self, key, value, ttl: float | None = None) -> None: ...
        def get(self, key): ...
        def __len__(self) -> int: ...

A least-recently-used cache with optional per-entry TTL.

- `clock` is a zero-argument callable returning a float "now" (so tests can control time).
- `put(k, v, ttl)`: insert/update. If `ttl` is not None the entry expires at now+ttl.
  Updating an existing key refreshes its value, its TTL, and its recency.
- `get(k)`: return the value, or None if missing or expired. A successful get refreshes
  recency. An expired entry must be removed as a side effect.
- When inserting a NEW key would exceed `capacity`, first drop any entries that are
  already expired; if still over capacity, evict the least-recently-used entry.
- `__len__` returns the number of live (non-expired) entries; it must not count
  expired ones, and it should purge them.

Return ONLY a fenced python code block containing the class.""",
        "test": """
t = {"now": 0.0}
clk = lambda: t["now"]
c = LRUTTLCache(2, clk)
c.put("a", 1); c.put("b", 2)
assert c.get("a") == 1
c.put("c", 3)              # 'b' is LRU (a was just read) -> evict b
assert c.get("b") is None
assert c.get("a") == 1 and c.get("c") == 3
assert len(c) == 2

# ttl expiry
c2 = LRUTTLCache(10, clk)
c2.put("x", 1, ttl=5)
t["now"] = 4.9
assert c2.get("x") == 1
t["now"] = 5.1
assert c2.get("x") is None
assert len(c2) == 0

# update refreshes ttl and recency
t["now"] = 0.0
c3 = LRUTTLCache(2, clk)
c3.put("a", 1, ttl=10); c3.put("b", 2)
t["now"] = 5.0
c3.put("a", 99, ttl=10)     # refresh a
t["now"] = 12.0
assert c3.get("a") == 99     # still alive (expires at 15)
assert len(c3) == 2

# expired entries are dropped before LRU eviction
t["now"] = 0.0
c4 = LRUTTLCache(2, clk)
c4.put("old", 1, ttl=1)
c4.put("keep", 2)
t["now"] = 2.0
c4.put("new", 3)
assert c4.get("keep") == 2
assert c4.get("new") == 3
assert c4.get("old") is None
""",
    },
    {
        "name": "parse_ini_nested",
        "prompt": """Write a Python function:

    def parse_config(text: str) -> dict:

Parse a small INI-like config format into nested dicts.

Rules:
- Lines that are blank or whose first non-space character is '#' or ';' are ignored.
- A line like `[a.b.c]` opens a section; it creates nested dicts: result["a"]["b"]["c"].
- `key = value` assigns into the current section (or top level before any section header).
- Keys and values are stripped of surrounding whitespace.
- The FIRST '=' splits the line; later '=' characters belong to the value.
- Values are coerced: "true"/"false" (case-insensitive) -> bool; a valid int -> int;
  a valid float -> float; otherwise str.
- A value wrapped in matching single or double quotes is always a string, with the
  quotes removed and NO coercion applied.
- A later assignment to the same key in the same section overwrites the earlier one.
- Re-opening an existing section merges into it rather than replacing it.

Return ONLY a fenced python code block containing the function.""",
        "test": """
cfg = parse_config('''
# comment
; also comment
top = 1

[server]
host = "localhost"
port = 8080
debug = TRUE
ratio = 0.5
name = hello world

[server.tls]
enabled = false
cert = /etc/x.pem

[server]
port = 9090
''')
assert cfg["top"] == 1
assert cfg["server"]["host"] == "localhost"
assert cfg["server"]["port"] == 9090          # overwrite via re-opened section
assert cfg["server"]["debug"] is True
assert cfg["server"]["ratio"] == 0.5
assert cfg["server"]["name"] == "hello world"
assert cfg["server"]["tls"]["enabled"] is False   # merged, not replaced
assert cfg["server"]["tls"]["cert"] == "/etc/x.pem"
# quoted numbers stay strings
c2 = parse_config('[a]\\nx = "123"\\ny = 123')
assert c2["a"]["x"] == "123" and isinstance(c2["a"]["x"], str)
assert c2["a"]["y"] == 123
# first '=' splits
c3 = parse_config("k = a=b=c")
assert c3["k"] == "a=b=c"
assert parse_config("") == {}
""",
    },
    {
        "name": "rate_limiter_window",
        "prompt": """Write a Python class:

    class SlidingWindowLimiter:
        def __init__(self, limit: int, window: float, clock): ...
        def allow(self, key: str) -> bool: ...
        def retry_after(self, key: str) -> float: ...

A per-key sliding-window rate limiter.

- `clock` is a zero-argument callable returning float seconds.
- `allow(key)`: returns True and records the hit if fewer than `limit` hits for that key
  occurred in the last `window` seconds (strictly: hits with timestamp > now - window).
  Otherwise returns False and records NOTHING.
- `retry_after(key)`: seconds until the next call to allow(key) would succeed. Returns
  0.0 if a call would succeed right now. Otherwise the time until the oldest in-window
  hit falls out of the window.
- Keys are independent. Old timestamps must not accumulate without bound.

Return ONLY a fenced python code block containing the class.""",
        "test": """
t = {"now": 100.0}
clk = lambda: t["now"]
L = SlidingWindowLimiter(3, 10.0, clk)
assert L.allow("a") is True
assert L.allow("a") is True
assert L.allow("a") is True
assert L.allow("a") is False
assert L.retry_after("a") == 10.0
# other key unaffected
assert L.allow("b") is True
assert L.retry_after("b") == 0.0
# denied calls record nothing -> still expires 10s after the 3rd hit
t["now"] = 109.9
assert L.allow("a") is False
t["now"] = 110.1
assert L.allow("a") is True
# partial expiry
t2 = {"now": 0.0}
clk2 = lambda: t2["now"]
M = SlidingWindowLimiter(2, 10.0, clk2)
assert M.allow("k") is True
t2["now"] = 5.0
assert M.allow("k") is True
assert M.allow("k") is False
assert abs(M.retry_after("k") - 5.0) < 1e-9
t2["now"] = 10.1
assert M.allow("k") is True
""",
    },
    {
        "name": "diff_lcs",
        "prompt": """Write a Python function:

    def unified_ops(a: list[str], b: list[str]) -> list[tuple[str, str]]:

Compute a minimal edit script transforming list `a` into list `b`, based on a longest
common subsequence.

Return a list of (op, line) tuples where op is one of:
  " " (context/unchanged), "-" (delete from a), "+" (insert from b)

The returned sequence, read in order, must:
  - contain every element of `a` exactly once as either " " or "-"
  - contain every element of `b` exactly once as either " " or "+"
  - have the maximum possible number of " " entries (i.e. use an LCS)

When a deletion and an insertion occur at the same position, emit ALL the deletions
for that run before the insertions.

Return ONLY a fenced python code block containing the function.""",
        "test": """
def check(a, b):
    ops = unified_ops(a, b)
    assert [l for o,l in ops if o in (" ","-")] == a, (a,b,ops)
    assert [l for o,l in ops if o in (" ","+")] == b, (a,b,ops)
    return sum(1 for o,_ in ops if o == " ")

assert unified_ops([], []) == []
assert unified_ops(["x"], ["x"]) == [(" ","x")]
assert unified_ops(["x"], []) == [("-","x")]
assert unified_ops([], ["y"]) == [("+","y")]
assert check(["a","b","c"], ["a","c"]) == 2
assert check(["a","b","c"], ["a","x","c"]) == 2
assert check(["a","b","c","d"], ["b","d"]) == 2
assert check(list("abcabba"), list("cbabac")) == 4
assert check(["1","2","3"], ["4","5","6"]) == 0
# deletions before insertions in a replace run
ops = unified_ops(["a","b","c"], ["a","x","c"])
i = [k for k,(o,l) in enumerate(ops) if o=="-"][0]
j = [k for k,(o,l) in enumerate(ops) if o=="+"][0]
assert i < j, ops
""",
    },
    {
        "name": "path_normalize",
        "prompt": """Write a Python function:

    def resolve(base: str, rel: str) -> str:

Resolve a POSIX-style path `rel` against directory `base`, purely lexically
(no filesystem access).

- If `rel` is absolute (starts with '/'), it is resolved from '/' and `base` is ignored.
- Otherwise resolve relative to `base`, which you may assume is an absolute path.
- Collapse '.' segments, resolve '..' segments, and squeeze repeated '/'.
- '..' at the root stays at the root ('/..' -> '/').
- The result must be absolute, must not end in '/' unless it is exactly '/'.
- An empty `rel` yields the normalized `base`.

Examples:
    resolve("/a/b", "c")        == "/a/b/c"
    resolve("/a/b", "../c")     == "/a/c"
    resolve("/a/b", "/x//y/")   == "/x/y"
    resolve("/a/b", "")         == "/a/b"
    resolve("/", "..")          == "/"

Return ONLY a fenced python code block containing the function.""",
        "test": """
assert resolve("/a/b", "c") == "/a/b/c"
assert resolve("/a/b", "../c") == "/a/c"
assert resolve("/a/b", "/x//y/") == "/x/y"
assert resolve("/a/b", "") == "/a/b"
assert resolve("/", "..") == "/"
assert resolve("/a/b", "../../..") == "/"
assert resolve("/a/b", "./././c") == "/a/b/c"
assert resolve("/a//b//", "c/../d") == "/a/b/d"
assert resolve("/a/b/", "/") == "/"
assert resolve("/a", "b/c/../../d") == "/a/d"
assert resolve("//a//b", "c") == "/a/b/c"
assert resolve("/a/b", "..") == "/a"
""",
    },
    {
        "name": "retry_backoff",
        "prompt": """Write a Python function:

    def backoff_schedule(attempts: int, base: float, cap: float,
                         mode: str = "exponential", factor: float = 2.0) -> list[float]:

Return the list of sleep durations BETWEEN attempts (so len == attempts - 1; an
`attempts` of 0 or 1 yields []).

- mode "exponential": delay_i = base * (factor ** i) for i = 0, 1, 2, ...
- mode "linear":      delay_i = base * (i + 1)
- mode "constant":    delay_i = base
- Every delay is clamped to at most `cap`.
- Negative `attempts` yields [].
- If base < 0 or cap < 0, raise ValueError.
- If mode is unknown, raise ValueError.
- Delays are floats.

Return ONLY a fenced python code block containing the function.""",
        "test": """
assert backoff_schedule(1, 1.0, 100.0) == []
assert backoff_schedule(0, 1.0, 100.0) == []
assert backoff_schedule(-3, 1.0, 100.0) == []
assert backoff_schedule(4, 1.0, 100.0) == [1.0, 2.0, 4.0]
assert backoff_schedule(5, 1.0, 3.0) == [1.0, 2.0, 3.0, 3.0]
assert backoff_schedule(4, 2.0, 100.0, mode="linear") == [2.0, 4.0, 6.0]
assert backoff_schedule(4, 2.0, 5.0, mode="linear") == [2.0, 4.0, 5.0]
assert backoff_schedule(3, 1.5, 100.0, mode="constant") == [1.5, 1.5]
assert backoff_schedule(4, 1.0, 100.0, factor=3.0) == [1.0, 3.0, 9.0]
try:
    backoff_schedule(3, -1.0, 10.0); raise AssertionError("expected ValueError")
except ValueError: pass
try:
    backoff_schedule(3, 1.0, -10.0); raise AssertionError("expected ValueError")
except ValueError: pass
try:
    backoff_schedule(3, 1.0, 10.0, mode="nope"); raise AssertionError("expected ValueError")
except ValueError: pass
assert all(isinstance(x, float) for x in backoff_schedule(4, 1, 100))
""",
    },
    {
        "name": "sql_where_builder",
        "prompt": """Write a Python function:

    def build_where(filters: dict) -> tuple[str, list]:

Build a parameterized SQL WHERE clause from a filter dict. Return (sql, params) where
`sql` uses '?' placeholders and `params` is the ordered list of bound values.

Keys are column names, optionally suffixed with '__op':
  - "col"        -> equality:            col = ?
  - "col__ne"    -> col != ?
  - "col__gt" / "__gte" / "__lt" / "__lte"  -> the obvious comparisons
  - "col__in"    -> col IN (?, ?, ...)   (value is a list/tuple)
  - "col__like"  -> col LIKE ?
  - "col__isnull" -> value True  -> "col IS NULL"   (no param)
                     value False -> "col IS NOT NULL" (no param)

Rules:
- Conditions are joined with " AND " in sorted-by-key order (sort by the full key
  including suffix) so output is deterministic.
- A value of None for a plain equality key means "col IS NULL" (no param).
- An empty list for "__in" produces the always-false condition "1 = 0" (no params).
- An empty `filters` dict returns ("", []).
- The returned sql has NO leading "WHERE".
- An unknown "__op" suffix raises ValueError.

Return ONLY a fenced python code block containing the function.""",
        "test": """
assert build_where({}) == ("", [])
assert build_where({"a": 1}) == ("a = ?", [1])
assert build_where({"b": 2, "a": 1}) == ("a = ? AND b = ?", [1, 2])
assert build_where({"a": None}) == ("a IS NULL", [])
assert build_where({"a__ne": 1}) == ("a != ?", [1])
assert build_where({"a__gt": 1}) == ("a > ?", [1])
assert build_where({"a__gte": 1}) == ("a >= ?", [1])
assert build_where({"a__lt": 1}) == ("a < ?", [1])
assert build_where({"a__lte": 1}) == ("a <= ?", [1])
assert build_where({"a__in": [1,2,3]}) == ("a IN (?, ?, ?)", [1,2,3])
assert build_where({"a__in": []}) == ("1 = 0", [])
assert build_where({"a__like": "x%"}) == ("a LIKE ?", ["x%"])
assert build_where({"a__isnull": True}) == ("a IS NULL", [])
assert build_where({"a__isnull": False}) == ("a IS NOT NULL", [])
s, p = build_where({"z": 1, "a__in": [7,8], "m__isnull": True})
assert s == "a IN (?, ?) AND m IS NULL AND z = ?", s
assert p == [7, 8, 1], p
try:
    build_where({"a__bogus": 1}); raise AssertionError("expected ValueError")
except ValueError: pass
""",
    },
]
