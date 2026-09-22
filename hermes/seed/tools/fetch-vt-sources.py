#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Build the seed corpus the sandboxed agent works from, on the host.

The agent runs with `AGENT_OFFLINE=1`, because three of four online runs spent
their whole budget researching sources the card told them not to look for. That
trade is worth keeping, but it means every byte the agent needs has to be on
disk before the container starts — so this fetches it.

What it produces, in ~/Git/agent-runs/seed-data/:

  vt-childcare-providers.json   1,048 licensed providers. Real business names,
                                and every row has a phone, an email, a county
                                and coordinates.
  vt-dfs-licensed-trades.json   11,489 licensed electricians, plumbers and gas
                                installers. Mostly sole traders, addressed.
  vt-website-probes.json        The part the agent cannot do offline: for every
                                distinct custom email domain, whether a site
                                answers and what shape it is in.

The web-presence signal is the point of the whole dataset, and it is derivable
here without guessing at domains: a provider emailing from gmail.com has no
business web presence worth the name, and one emailing from its own domain has
something whose quality can be measured. BRIEF.md's "Website quality" section
lists the signals; this collects the ones obtainable without a paid key.
"""

from __future__ import annotations

import json
import re
import ssl
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

OUT = Path.home() / "Git/agent-runs/seed-data"
UA = "vt-smb-dataset/0.1 (personal prospect-list project; contact via repo owner)"

# Mail providers that tell you the business has no domain of its own. The list is
# deliberately generous with regional ISPs — myfairpoint and comcast addresses are
# all over rural Vermont and mean exactly what gmail means.
FREEMAIL = {
    "gmail.com", "yahoo.com", "hotmail.com", "aol.com", "outlook.com", "comcast.net",
    "icloud.com", "msn.com", "me.com", "live.com", "myfairpoint.net", "verizon.net",
    "att.net", "sbcglobal.net", "mac.com", "yahoo.co.uk", "ymail.com", "gmail.co",
    "vermontel.net", "together.net", "burlingtontelecom.net", "charter.net", "juno.com",
}

SOCRATA = [
    ("ctdw-tmfz", "vt-childcare-providers.json", "child care providers"),
    ("cy8e-89cz", "vt-dfs-licensed-trades.json", "DFS licensed trades"),
]

# OpenStreetMap, via Overpass. Needs a User-Agent — the default curl one gets a
# bare 406 from overpass-api.de.
#
# MEASURED 2026-09-22, because the plan assumed this would enrich the trades and
# it does not: of 11,489 licensed trades, 31 surname+town matched an OSM POI and
# spot-checking showed them to be false ("Block" the gas installer vs H&R Block).
# OSM maps PREMISES. A sole-trader electrician working out of a van at a home
# address is not a mapped feature, and only 36 OSM names even look like a trade.
#
# It is still worth fetching, for the opposite reason: 3,068 named Vermont
# businesses, 1,054 with a phone, 238 with a phone and NO website, and 77 whose
# entire web presence is a Facebook page. That is a NEW prospect pool, not an
# enrichment of an old one.
OVERPASS = "https://overpass-api.de/api/interpreter"
OVERPASS_QUERY = """[out:json][timeout:300];
area["ISO3166-2"="US-VT"][admin_level=4]->.vt;
(
  nwr["craft"](area.vt);
  nwr["office"](area.vt);
  nwr["shop"](area.vt);
  nwr["amenity"~"^(contractor|car_repair|veterinary|dentist|doctors)$"](area.vt);
);
out tags center;"""

PARKED = re.compile(
    r"(domain (is )?for sale|this domain|parked (free )?(at|by)|buy this domain"
    r"|godaddy|sedoparking|hugedomains|under construction|coming soon"
    r"|default web page|it works!|welcome to nginx|apache2 ubuntu default)",
    re.I,
)


def fetch_socrata(rid: str, label: str) -> list[dict]:
    rows, off = [], 0
    while True:
        url = f"https://data.vermont.gov/resource/{rid}.json?$limit=5000&$offset={off}"
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        page = json.load(urllib.request.urlopen(req, timeout=120))
        rows += page
        if len(page) < 5000:
            break
        off += 5000
        time.sleep(1)
    print(f"  {label}: {len(rows)} rows")
    return rows


def probe(domain: str) -> dict:
    """One domain, https first then http. Never raises — a failure is a finding."""
    out: dict = {"domain": domain, "reachable": False, "scheme": None, "status": None,
                 "final_url": None, "ttfb_ms": None, "bytes": None, "title": None,
                 "has_viewport": None, "parked": None, "copyright_year": None,
                 "error": None, "probed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    ctx = ssl.create_default_context()
    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            t0 = time.perf_counter()
            with urllib.request.urlopen(req, timeout=12, context=ctx) as r:
                ttfb = (time.perf_counter() - t0) * 1000
                body = r.read(200_000).decode("utf-8", "replace")
                out.update(reachable=True, scheme=scheme, status=r.status,
                           final_url=r.url, ttfb_ms=round(ttfb), bytes=len(body))
            m = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
            out["title"] = re.sub(r"\s+", " ", m.group(1)).strip()[:120] if m else None
            out["has_viewport"] = bool(re.search(r'<meta[^>]+name=["\']viewport', body, re.I))
            out["parked"] = bool(PARKED.search(body[:4000]))
            years = re.findall(r"(?:©|&copy;|copyright)[^0-9]{0,20}(19|20)(\d\d)", body, re.I)
            if years:
                out["copyright_year"] = max(int(a + b) for a, b in years)
            return out
        except urllib.error.HTTPError as e:
            # An error status is still a live server, and a 403/503 is not "no site".
            out.update(reachable=True, scheme=scheme, status=e.code, final_url=url)
            return out
        except Exception as e:
            out["error"] = f"{type(e).__name__}"
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    print("fetching Vermont open data")
    providers = None
    for rid, fn, label in SOCRATA:
        rows = fetch_socrata(rid, label)
        (OUT / fn).write_text(json.dumps(rows))
        if "childcare" in fn:
            providers = rows

    domains = set()
    for r in providers or []:
        m = re.search(r"@([\w.-]+)", (r.get("email_address") or "").lower())
        if m and m.group(1) not in FREEMAIL:
            domains.add(m.group(1))
    print(f"\nprobing {len(domains)} custom email domains "
          f"(the freemail ones need no probe — that IS the finding)")

    with ThreadPoolExecutor(max_workers=12) as pool:
        probes = list(pool.map(probe, sorted(domains)))
    (OUT / "vt-website-probes.json").write_text(json.dumps(probes, indent=1))

    live = [p for p in probes if p["reachable"]]
    print(f"  reachable: {len(live)}/{len(probes)}")
    print(f"  no viewport (pre-mobile):  {sum(1 for p in live if p['has_viewport'] is False)}")
    print(f"  parked/placeholder:        {sum(1 for p in live if p['parked'])}")
    print(f"  copyright year <= 2020:    {sum(1 for p in live if (p['copyright_year'] or 9999) <= 2020)}")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
