#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib"]
# ///
"""Room temperatures beside each Mitsubishi head, as a PDF and CSV for the installer.

The heads cannot be read directly (no Kumo, no CN105 adapter yet), so each room's
own sensor or thermostat stands in. Room data comes from Prometheus, which scrapes
Home Assistant every minute and keeps 90 days; query through Grafana's datasource
proxy, the one hostname reachable over the tailnet. Outdoor weather is measured
at the KFSO airport station, read from NWS for the last week and from Prometheus before that.

Usage:
    heat-pump-report.py                       # the last 7 days
    heat-pump-report.py --since 2026-10-14 --until 2026-10-21
    heat-pump-report.py --days 3 --out ~/Desktop/heat-pumps
"""

from __future__ import annotations

import argparse
import bisect
import csv
import json
import os
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

PROMETHEUS = os.environ.get(
    "PROMETHEUS_URL", "https://grafana.grehg2.xyz/api/datasources/proxy/uid/prometheus"
)
# Franklin County State Airport, Highgate: about 6 mi from the house.
NWS = "https://api.weather.gov/stations/KFSO/observations"
NWS_AGENT = "home-lab heat-pump-report (grehg2.xyz)"
TZ = ZoneInfo("America/New_York")
# Prometheus refuses a range query over 11,000 points.
MAX_POINTS = 2000


@dataclass(frozen=True)
class Room:
    name: str
    source: str
    temp_query: str | None
    # A climate entity whose "heating" action is shaded on the chart.
    call_entity: str | None = None
    call_label: str = ""


@dataclass(frozen=True)
class OutdoorUnit:
    model: str
    serial: str
    refrigerant: str
    rooms: tuple[Room, ...]


def sensor(entity: str) -> str:
    return f'hass_sensor_temperature_celsius{{entity="{entity}"}}'


def thermostat(entity: str) -> str:
    return f'hass_climate_current_temperature_celsius{{entity="{entity}"}}'


# From notes/heat-pump-and-mini-splits.md. None = not in Home Assistant yet.
UNITS = (
    OutdoorUnit("MXZ-3C30NAHZ4", "33P10932", "R410A", (
        Room("Children's room", "Zigbee sensor (Isaacs Room)", sensor("sensor.0x282c02bfffe3a49e_temperature")),
        Room("Guest room", "Zigbee sensor", sensor("sensor.guest_bedroom_temperature")),
    )),
    OutdoorUnit("MXZ-3C30NAHZ4", "33P10945", "R410A", (
        Room("Dining room", "T6 Pro thermostat (boiler zone)",
             thermostat("climate.1st_floor_thermostat"),
             call_entity="climate.1st_floor_thermostat", call_label="boiler zone calling for heat"),
        Room("Master bedroom", "T6 Pro thermostat (boiler zone)",
             thermostat("climate.2nd_floor_thermostat"),
             call_entity="climate.2nd_floor_thermostat", call_label="boiler zone calling for heat"),
    )),
    # The kitchen thermostat driving this head is not Z-Wave.
    OutdoorUnit("MUZ-FX24NLHZ", "4001455T20U4G5", "R454B", (
        Room("Living room", "no sensor yet", None),
    )),
    OutdoorUnit("unknown model", "unknown serial", "R454B", (
        Room("Basement", "Zigbee sensor", sensor("sensor.basement_temperature")),
    )),
)


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)


def step_seconds(start: datetime, end: datetime) -> int:
    return max(60, int((end - start).total_seconds() // MAX_POINTS))


def c_to_f(c: float) -> float:
    return c * 9 / 5 + 32


def query_range(query: str, start: datetime, end: datetime) -> list[tuple[float, float]]:
    """One series as (unix time, value); several series are merged by max."""
    params = urlencode({
        "query": f"max({query})",
        "start": start.timestamp(),
        "end": end.timestamp(),
        "step": step_seconds(start, end),
    })
    body = fetch_json(f"{PROMETHEUS}/api/v1/query_range?{params}")
    if body.get("status") != "success":
        raise RuntimeError(f"Prometheus: {body.get('error', body)}")
    return parse_matrix(body)


def parse_matrix(body: dict) -> list[tuple[float, float]]:
    result = body["data"]["result"]
    if not result:
        return []
    return [(float(t), float(v)) for t, v in result[0]["values"]]


def heating_spans(points: list[tuple[float, float]], step: int) -> list[tuple[float, float]]:
    """Runs of value 1 as (start, end) times; a gap ends a run."""
    spans: list[tuple[float, float]] = []
    for t, v in points:
        if v < 1:
            continue
        if spans and t - spans[-1][1] <= step:
            spans[-1] = (spans[-1][0], t)
        else:
            spans.append((t, t))
    return [(a, b + step) for a, b in spans]


def outdoor(start: datetime, end: datetime) -> list[tuple[float, float, float | None]]:
    """(unix time, °F, RH %) measured at KFSO, oldest first.

    NWS keeps about 7 days, so anything older comes from Home Assistant's copy
    in Prometheus, recorded since 2026-10-27.
    """
    rows = nws_observations(start, end)
    first = rows[0][0] if rows else end.timestamp()
    if start.timestamp() < first - 3600:
        rows = recorded_outdoor(start, datetime.fromtimestamp(first, timezone.utc)) + rows
    return rows


def nws_observations(start: datetime, end: datetime) -> list[tuple[float, float, float | None]]:
    url = f"{NWS}?" + urlencode({"start": _utc(start), "end": _utc(end)})
    rows = []
    while url:
        req = urllib.request.Request(url, headers={"User-Agent": NWS_AGENT, "Accept": "application/geo+json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.load(resp)
        page = parse_observations(body)
        rows += page
        # The next link drops start and end, so stop once past start.
        nxt = body.get("pagination", {}).get("next")
        url = nxt if page and min(page)[0] > start.timestamp() and nxt != url else None
    return sorted(r for r in set(rows) if start.timestamp() <= r[0] <= end.timestamp())


def parse_observations(body: dict) -> list[tuple[float, float, float | None]]:
    rows = []
    for f in body.get("features", []):
        p = f["properties"]
        temp, rh = p["temperature"]["value"], p["relativeHumidity"]["value"]
        if temp is not None:
            ts = datetime.fromisoformat(p["timestamp"]).timestamp()
            rows.append((ts, round(c_to_f(temp), 1), None if rh is None else round(rh)))
    return rows


def recorded_outdoor(start: datetime, end: datetime) -> list[tuple[float, float, float | None]]:
    temps = query_range('hass_sensor_temperature_celsius{entity="sensor.outdoor_temperature_kfso"}', start, end)
    rh = dict(query_range('hass_sensor_humidity_percent{entity="sensor.outdoor_humidity_kfso"}', start, end))
    return [(t, round(c_to_f(v), 1), rh.get(t)) for t, v in temps]


def _utc(d: datetime) -> str:
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def collect(start: datetime, end: datetime) -> dict:
    step = step_seconds(start, end)
    temps, calls = {}, {}
    for unit in UNITS:
        for room in unit.rooms:
            if room.temp_query:
                temps[room.name] = [(t, c_to_f(v)) for t, v in query_range(room.temp_query, start, end)]
            if room.call_entity:
                q = f'hass_climate_action{{entity="{room.call_entity}",action="heating"}}'
                calls[room.name] = heating_spans(query_range(q, start, end), step)
    return {"temps": temps, "calls": calls, "outdoor": outdoor(start, end), "step": step}


def write_csv(path: Path, data: dict) -> None:
    rooms = list(data["temps"])
    by_time: dict[float, dict[str, float]] = {}
    for room, points in data["temps"].items():
        for t, v in points:
            by_time.setdefault(t, {})[room] = v
    out_times = [t for t, _, _ in data["outdoor"]]
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time (America/New_York)", *[f"{r} °F" for r in rooms], "outdoor °F", "outdoor RH %"])
        for t in sorted(by_time):
            # Each row takes the latest reading before it.
            i = bisect.bisect_right(out_times, t) - 1
            _, temp, rh = data["outdoor"][i] if i >= 0 else (t, "", "")
            rh = "" if rh is None else rh
            local = datetime.fromtimestamp(t, TZ).strftime("%Y-%m-%d %H:%M")
            w.writerow([local, *[_fmt(by_time[t].get(r)) for r in rooms], temp, rh])


def _fmt(v: float | None) -> str:
    return "" if v is None else f"{v:.1f}"


def write_pdf(path: Path, data: dict, start: datetime, end: datetime) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    def local(ts: float) -> datetime:
        return datetime.fromtimestamp(ts, TZ)

    period = f"{local(start.timestamp()):%a %b %-d %Y, %-I:%M %p} to {local(end.timestamp()):%a %b %-d %Y, %-I:%M %p} (Eastern)"
    with PdfPages(path) as pdf:
        fig = plt.figure(figsize=(11, 8.5))
        fig.text(0.06, 0.92, "Heat pump room temperatures", fontsize=20, weight="bold")
        fig.text(0.06, 0.88, f"Sheldon, VT · {period}", fontsize=11)
        lines = summary_lines(data)
        fig.text(0.06, 0.82, "\n".join(lines), fontsize=10, family="monospace", va="top")
        pdf.savefig(fig)
        plt.close(fig)

        out_t = [local(t) for t, _, _ in data["outdoor"]]
        out_f = [f for _, f, _ in data["outdoor"]]
        out_rh = [float("nan") if rh is None else rh for _, _, rh in data["outdoor"]]
        for unit in UNITS:
            fig, (ax, ax_rh) = plt.subplots(2, 1, figsize=(11, 8.5), sharex=True,
                                            gridspec_kw={"height_ratios": [4, 1]})
            fig.suptitle(f"Outdoor unit {unit.model} · serial {unit.serial} · {unit.refrigerant}",
                         fontsize=14, weight="bold")
            ax.plot(out_t, out_f, color="0.55", lw=1.2, ls="--", label="Outdoor (KFSO, Highgate airport)")
            missing = []
            for room in unit.rooms:
                points = data["temps"].get(room.name)
                if not points:
                    missing.append(f"{room.name}: no data ({room.source})")
                    continue
                ax.plot([local(t) for t, _ in points], [v for _, v in points], lw=1.6,
                        label=f"{room.name} ({room.source})")
                for i, (a, b) in enumerate(data["calls"].get(room.name, [])):
                    ax.axvspan(local(a), local(b), color="tab:orange", alpha=0.15,
                               label=f"{room.name}: {room.call_label}" if i == 0 else None)
            ax.axhline(32, color="tab:blue", lw=0.6, alpha=0.5)
            ax.set_ylabel("°F")
            ax.grid(alpha=0.3)
            ax.legend(loc="upper left", fontsize=8)
            if missing:
                ax.text(0.99, 0.02, "\n".join(missing), transform=ax.transAxes, ha="right",
                        va="bottom", fontsize=8, color="tab:red")
            ax_rh.plot(out_t, out_rh, color="0.55", lw=1)
            ax_rh.set_ylabel("Outdoor RH %")
            ax_rh.grid(alpha=0.3)
            ax_rh.xaxis.set_major_formatter(mdates.DateFormatter("%a %-m/%-d\n%-I %p", tz=TZ))
            fig.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)


def summary_lines(data: dict) -> list[str]:
    lines = [f"{'Room':<17}{'Outdoor unit':<28}{'Min °F':>8}{'Mean °F':>9}{'Max °F':>8}", ""]
    for unit in UNITS:
        for room in unit.rooms:
            vals = [v for _, v in data["temps"].get(room.name, [])]
            label = f"{unit.model} {unit.serial}"
            if vals:
                lines.append(f"{room.name:<17}{label:<28}{min(vals):>8.1f}{sum(vals) / len(vals):>9.1f}{max(vals):>8.1f}")
            else:
                lines.append(f"{room.name:<17}{label:<28}{'no sensor in Home Assistant yet':>25}")
    temps = [f for _, f, _ in data["outdoor"]]
    if temps:
        lines += ["", f"Outdoor: {min(temps):.0f} to {max(temps):.0f} °F"]
    lines += [
        "",
        "Room temperatures come from a sensor or thermostat in each room, not",
        "from the heads. Samples every "
        f"{data['step'] // 60} min. Raw data is in the CSV beside this PDF.",
    ]
    return lines


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--days", type=float, default=7, help="how far back from --until (default 7)")
    p.add_argument("--since", help="start date or datetime, Eastern (overrides --days)")
    p.add_argument("--until", help="end date or datetime, Eastern (default now)")
    p.add_argument("--out", type=Path, help="output directory (default ./heat-pump-report-<dates>)")
    return p.parse_args(argv)


def parse_local(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=TZ)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    end = parse_local(args.until) if args.until else datetime.now(TZ)
    start = parse_local(args.since) if args.since else end - timedelta(days=args.days)
    out = args.out or Path(f"heat-pump-report-{start:%Y-%m-%d}_{end:%Y-%m-%d}")
    out.mkdir(parents=True, exist_ok=True)
    try:
        data = collect(start, end)
    except (URLError, RuntimeError) as e:
        print(f"heat-pump-report: could not fetch data: {e}", file=sys.stderr)
        return 1
    write_csv(out / "heat-pumps.csv", data)
    write_pdf(out / "heat-pumps.pdf", data, start, end)
    print(out / "heat-pumps.pdf")
    print(out / "heat-pumps.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
