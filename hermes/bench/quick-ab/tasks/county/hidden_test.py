import json, subprocess
from pathlib import Path
from cc.stats import capacity_by_county

DATA = Path("data/providers.json")
ROWS = json.loads(DATA.read_text())

def expected(min_stars=None):
    agg = {}
    for r in ROWS:
        s = r["current_stars_level"]
        if min_stars is not None and (not s[0].isdigit() or int(s[0]) < min_stars):
            continue
        n, c = agg.get(r["county"], (0, 0))
        agg[r["county"]] = (n + 1, c + int(r["total_licensed_capacity"]))
    return sorted(((k, n, c) for k, (n, c) in agg.items()), key=lambda t: (-t[2], t[0]))

def test_all():
    assert [tuple(t) for t in capacity_by_county(DATA)] == expected()

def test_first_row():
    assert tuple(capacity_by_county(DATA)[0]) == ("Chittenden", 208, 10740)

def test_min_stars_4():
    assert [tuple(t) for t in capacity_by_county(DATA, min_stars=4)] == expected(4)

def test_min_stars_1_drops_not_rated():
    got = capacity_by_county(DATA, min_stars=1)
    assert sum(t[1] for t in got) == 1045

def test_cli():
    out = subprocess.run(["uv", "run", "--quiet", "cc", "capacity", "--min-stars", "5"],
                         capture_output=True, text=True, check=True).stdout
    lines = [l.strip() for l in out.strip().splitlines()]
    assert lines[0] == "county,providers,capacity"
    assert lines[1:] == [f"{a},{b},{c}" for a, b, c in expected(5)]
