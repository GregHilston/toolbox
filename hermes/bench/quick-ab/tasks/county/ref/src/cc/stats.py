import json
def capacity_by_county(path, min_stars=None):
    agg = {}
    for r in json.load(open(path)):
        s = r["current_stars_level"]
        if min_stars is not None and (not s[0].isdigit() or int(s[0]) < min_stars):
            continue
        n, c = agg.get(r["county"], (0, 0))
        agg[r["county"]] = (n + 1, c + int(r["total_licensed_capacity"]))
    return sorted(((k, n, c) for k, (n, c) in agg.items()), key=lambda t: (-t[2], t[0]))
