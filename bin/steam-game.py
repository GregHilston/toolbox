#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""A Steam game's price, review score, Steam Deck rating and Linux support.

Keyless, but unofficial: the store's own storesearch, appdetails, appreviews and
Deck-compatibility endpoints, plus ProtonDB's summary file. They have been
stable for years; a KeyError here means one of them changed shape.

Usage:
    steam-game.py "hades"
    steam-game.py 1145360
    steam-game.py "https://store.steampowered.com/app/1145360/Hades/" --country gb
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

STORE = "https://store.steampowered.com"
PROTONDB = "https://www.protondb.com/api/v1/reports/summaries/{}.json"
UA = "toolbox-steam-game/1.0 (https://github.com/GregHilston/toolbox)"

DECK = {0: "Unknown", 1: "Unsupported", 2: "Playable", 3: "Verified"}
STEAMOS = {0: "Unknown", 1: "Unsupported", 2: "Compatible"}
DECK_PASS = 4  # display_type of a passed Deck test; the rest are caveats


class SteamError(Exception):
    pass


def _get(url: str) -> dict | None:
    """Parsed JSON, or None on a 404."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        if e.code == 404:
            return None
        raise


def find(query: str, country: str) -> tuple[int, list[dict]]:
    """(appid, other matches). An exact name wins over Steam's relevance order."""
    if m := re.fullmatch(r"\d+|.*store\.steampowered\.com/app/(\d+).*", query.strip()):
        return int(m.group(1) or m.group(0)), []
    items = (_get(f"{STORE}/api/storesearch/?" + urlencode({"term": query, "cc": country, "l": "en"})) or {}).get("items") or []
    apps = [{"id": i["id"], "name": i["name"]} for i in items if i.get("type") == "app"]
    if not apps:
        raise SteamError(f'no Steam game matches "{query}"')
    best = next((a for a in apps if a["name"].casefold() == query.strip().casefold()), apps[0])
    return best["id"], [a for a in apps if a is not best]


def details(appid: int, country: str) -> dict:
    resp = _get(f"{STORE}/api/appdetails?" + urlencode({"appids": appid, "cc": country, "l": "en"})) or {}
    # Keyed by an id that is not always the one asked for, so take the only entry.
    entry = next(iter(resp.values()), {})
    if not entry.get("success"):
        raise SteamError(f"Steam has no store page for app {appid}")
    return entry["data"]


def reviews(appid: int) -> dict:
    q = urlencode({"json": 1, "language": "all", "purchase_type": "all", "num_per_page": 0})
    return (_get(f"{STORE}/appreviews/{appid}?{q}") or {}).get("query_summary") or {}


def deck(appid: int) -> dict:
    q = urlencode({"nAppID": appid, "l": "english"})
    return (_get(f"{STORE}/saleaction/ajaxgetdeckappcompatibilityreport?{q}") or {}).get("results") or {}


def protondb(appid: int) -> dict | None:
    return _get(PROTONDB.format(appid))


def _caveat(token: str) -> str:
    words = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", token.rsplit("_", 1)[-1])
    return words[:1] + words[1:].lower()


def format_game(appid: int, d: dict, r: dict, dk: dict, pdb: dict | None, others: list[dict]) -> str:
    lines = [f"# {d['name']} (app {appid})", f"{STORE}/app/{appid}", ""]
    release = d.get("release_date") or {}
    meta = [", ".join(d.get("developers") or []),
            ("coming " if release.get("coming_soon") else "released ") + (release.get("date") or "date unknown"),
            ", ".join(g["description"] for g in d.get("genres") or [])]
    lines += [" · ".join(m for m in meta if m), "", d.get("short_description") or "", ""]

    price = d.get("price_overview")
    if d.get("is_free"):
        lines.append("Price: free")
    elif price and price.get("discount_percent"):
        lines.append(f"Price: {price['final_formatted']} ({price['discount_percent']}% off {price['initial_formatted']})")
    elif price:
        lines.append(f"Price: {price['final_formatted']}")
    else:
        lines.append("Price: not for sale in this country")

    if r.get("total_reviews"):
        pct = round(100 * r["total_positive"] / r["total_reviews"])
        lines.append(f"Steam reviews: {r['review_score_desc']}, {pct}% positive of {r['total_reviews']:,}")
    else:
        lines.append("Steam reviews: none yet")
    if (mc := d.get("metacritic")) and mc.get("score"):
        lines.append(f"Metacritic: {mc['score']}")

    caveats = [_caveat(i["loc_token"]) for i in dk.get("resolved_items") or [] if i.get("display_type") != DECK_PASS]
    lines.append(f"Steam Deck: {DECK.get(dk.get('resolved_category', 0), 'Unknown')}"
                 + (f" (notes: {'; '.join(caveats)})" if caveats else ""))
    lines.append(f"SteamOS: {STEAMOS.get(dk.get('steamos_resolved_category', 0), 'Unknown')}")
    lines.append(f"Native Linux build: {'yes' if (d.get('platforms') or {}).get('linux') else 'no'}")
    if pdb:
        lines.append(f"ProtonDB: {pdb['tier'].title()} ({pdb['total']} reports, {pdb['confidence']} confidence,"
                     f" trending {pdb['trendingTier'].title()})")
    else:
        lines.append("ProtonDB: no reports")

    if others:
        lines += ["", "Other matches: " + "; ".join(f"{a['name']} ({a['id']})" for a in others[:5])]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Steam price, reviews, Steam Deck and Linux support for a game.")
    parser.add_argument("game", help="a name, an app id, or a store URL")
    parser.add_argument("--country", default="us", help="store country for prices (default: us)")
    args = parser.parse_args()
    try:
        appid, others = find(args.game, args.country)
        print(format_game(appid, details(appid, args.country), reviews(appid), deck(appid), protondb(appid), others))
    except SteamError as e:
        sys.exit(f"steam-game: {e}")
    except (URLError, TimeoutError, KeyError, ValueError) as e:
        sys.exit(f"steam-game: a Steam or ProtonDB request failed: {e!r}")


if __name__ == "__main__":
    main()
