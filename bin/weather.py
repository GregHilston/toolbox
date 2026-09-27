#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Current conditions and the forecast, from Open-Meteo. No key needed.

The one weather client: Hermes bots run it, and the home-lab digest reads its
`--json` output. It defaults to home (Sheldon, VT); `--place` geocodes any other
town through Open-Meteo, so a US state after a comma may be abbreviated.

Usage:
    weather.py
    weather.py --place "Burlington, VT" --days 5
    weather.py --json | jq '.days[0]'
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import date
from urllib.error import URLError
from urllib.parse import urlencode

HOME = ("Sheldon, VT", 44.884037, -73.001239)
FORECAST = "https://api.open-meteo.com/v1/forecast"
GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"

# WMO weather codes, as Open-Meteo reports them.
CODES = {
    0: ("Clear", "☀️"),
    1: ("Mostly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Fog", "🌫️"),
    48: ("Freezing fog", "🌫️"),
    51: ("Light drizzle", "🌦️"),
    53: ("Drizzle", "🌦️"),
    55: ("Heavy drizzle", "🌧️"),
    56: ("Freezing drizzle", "🌧️"),
    57: ("Freezing drizzle", "🌧️"),
    61: ("Light rain", "🌦️"),
    63: ("Rain", "🌧️"),
    65: ("Heavy rain", "🌧️"),
    66: ("Freezing rain", "🌧️"),
    67: ("Freezing rain", "🌧️"),
    71: ("Light snow", "🌨️"),
    73: ("Snow", "🌨️"),
    75: ("Heavy snow", "❄️"),
    77: ("Snow grains", "🌨️"),
    80: ("Showers", "🌦️"),
    81: ("Showers", "🌧️"),
    82: ("Violent showers", "⛈️"),
    85: ("Snow showers", "🌨️"),
    86: ("Heavy snow showers", "❄️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm, hail", "⛈️"),
    99: ("Thunderstorm, hail", "⛈️"),
}

STATES = dict(
    s.split(":")
    for s in "AL:Alabama AK:Alaska AZ:Arizona AR:Arkansas CA:California CO:Colorado "
    "CT:Connecticut DE:Delaware FL:Florida GA:Georgia HI:Hawaii ID:Idaho IL:Illinois "
    "IN:Indiana IA:Iowa KS:Kansas KY:Kentucky LA:Louisiana ME:Maine MD:Maryland "
    "MA:Massachusetts MI:Michigan MN:Minnesota MS:Mississippi MO:Missouri MT:Montana "
    "NE:Nebraska NV:Nevada NH:New_Hampshire NJ:New_Jersey NM:New_Mexico NY:New_York "
    "NC:North_Carolina ND:North_Dakota OH:Ohio OK:Oklahoma OR:Oregon PA:Pennsylvania "
    "RI:Rhode_Island SC:South_Carolina SD:South_Dakota TN:Tennessee TX:Texas UT:Utah "
    "VT:Vermont VA:Virginia WA:Washington WV:West_Virginia WI:Wisconsin WY:Wyoming".split()
)


class WeatherError(Exception):
    pass


def describe(code: int) -> tuple[str, str]:
    return CODES.get(code, ("Unknown", "🌡️"))


def _get(url: str, params: dict) -> dict:
    try:
        with urllib.request.urlopen(f"{url}?{urlencode(params)}", timeout=20) as resp:
            return json.loads(resp.read())
    except (URLError, TimeoutError, ValueError) as e:
        raise WeatherError(f"{url} failed: {e!r}") from e


def geocode(place: str) -> tuple[str, float, float]:
    """(label, lat, lon) for "Town" or "Town, State/Country"."""
    name, _, qualifier = (s.strip() for s in place.partition(","))
    # Both readings: "CA" is California and Canada.
    wanted = {qualifier.lower(), STATES.get(qualifier.upper(), "").replace("_", " ").lower()} - {""}
    if "uk" in wanted:
        wanted.add("gb")  # Open-Meteo's code for the UK
    hits = _get(GEOCODE, {"name": name, "count": 10}).get("results") or []
    if wanted:
        hits = [
            h for h in hits
            if wanted & {str(h.get(k, "")).lower() for k in ("admin1", "country", "country_code")}
        ]
    if not hits:
        raise WeatherError(f'no place called "{place}": try the town alone, or "Town, State"')
    h = hits[0]
    label = ", ".join(p for p in (h["name"], h.get("admin1"), h.get("country")) if p)
    return label, h["latitude"], h["longitude"]


def fetch(lat: float, lon: float, days: int) -> dict:
    return _get(FORECAST, {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,"
        "precipitation_probability_max,weather_code",
        "hourly": "temperature_2m,precipitation_probability,precipitation,weather_code",
        "temperature_unit": "fahrenheit",
        "precipitation_unit": "inch",
        "wind_speed_unit": "mph",
        "timezone": "auto",
        "past_days": 1,
        "forecast_days": days,
    })


def _named(code: int) -> dict:
    what, icon = describe(code)
    return {"code": code, "summary": what, "icon": icon}


def parse(data: dict, location: str) -> dict:
    """Now, yesterday, each forecast day, and today's hours. Daily row 0 is yesterday."""
    d, h, c = data["daily"], data["hourly"], data["current"]
    days = [
        {
            "date": d["time"][i],
            "high_f": d["temperature_2m_max"][i],
            "low_f": d["temperature_2m_min"][i],
            "precip_in": d["precipitation_sum"][i] or 0.0,
            "precip_chance": d["precipitation_probability_max"][i] or 0,
            **_named(d["weather_code"][i]),
        }
        for i in range(len(d["time"]))
    ]
    today = days[1]["date"]
    hours = [
        {"time": t, "temp_f": temp, "precip_chance": chance or 0, "precip_in": amount or 0.0, **_named(code)}
        for t, temp, chance, amount, code in zip(
            h["time"], h["temperature_2m"], h["precipitation_probability"], h["precipitation"], h["weather_code"]
        )
        if t.startswith(today)
    ]
    return {
        "location": location,
        "now": {
            "time": c["time"],
            "temp_f": c["temperature_2m"],
            "feels_like_f": c["apparent_temperature"],
            "wind_mph": c["wind_speed_10m"],
            **_named(c["weather_code"]),
        },
        "yesterday": days[0],
        "days": days[1:],
        "hours": hours,
    }


def format_text(w: dict) -> str:
    n = w["now"]
    lines = [
        f"# Weather in {w['location']}",
        "",
        f"Now: {n['summary']}, {n['temp_f']:.0f}°F (feels {n['feels_like_f']:.0f}°F), wind {n['wind_mph']:.0f} mph",
        "",
    ]
    for d in w["days"]:
        day = date.fromisoformat(d["date"]).strftime("%a %b %-d")
        rain = f"{d['precip_chance']}% chance, {d['precip_in']:.2f} in" if d["precip_chance"] else "dry"
        lines.append(f"{day}: {d['summary']}, high {d['high_f']:.0f}°F, low {d['low_f']:.0f}°F, {rain}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Current weather and forecast from Open-Meteo.")
    parser.add_argument("--place", help=f'town, e.g. "Burlington, VT" (default: {HOME[0]})')
    parser.add_argument("--days", type=int, default=3, help="forecast days, 1-16 (default: 3)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()
    if not 1 <= args.days <= 16:
        sys.exit("weather: --days must be 1 to 16")
    try:
        label, lat, lon = geocode(args.place) if args.place else HOME
        w = parse(fetch(lat, lon, args.days), label)
    except (WeatherError, KeyError, IndexError) as e:
        sys.exit(f"weather: {e}")
    print(json.dumps(w, indent=1, ensure_ascii=False) if args.json else format_text(w))


if __name__ == "__main__":
    main()
