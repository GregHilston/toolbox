#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib"]
# ///
"""Chart room temperatures over a few hours, with events marked, as a PNG.

For a short window you want to point at ("I turned the heads on here, then the
heat stopped"). The rooms, sensors and outdoor units come from heat-pump-report.py,
so both stay on one map. Each room gets its own panel on one shared °F scale, so a
small change is not drawn as a big one. The bottom strip shows when each boiler
zone called for heat, and a thermostat's setpoint is drawn on its own room's panel.

Usage:
    room-temps.py --list
    room-temps.py guest dining basement --since 6am
    room-temps.py basement --since 6:00 --until 11:00 --mark "7:40=Basement head on"
    room-temps.py guest --since "2026-10-27 06:00" --mark "~7:33=Head on" --plain --out /tmp/a.png
    room-temps.py basement --since 6:30am --share --stall --setpoint basement=70 --out /tmp/phil.png

A mark whose time starts with "~" is an estimate, drawn dotted and labelled "about".
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from urllib.error import URLError


def _load_report():
    path = Path(__file__).resolve().parent / "heat-pump-report.py"
    spec = importlib.util.spec_from_file_location("_heat_pump_report", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


report = _load_report()
TZ = report.TZ

ZONES = {
    "climate.1st_floor_thermostat": "1st floor zone",
    "climate.2nd_floor_thermostat": "2nd floor zone",
}
# Categorical slots, keyed to the room so its color never changes between charts.
COLORS = {
    "Guest room": "#2a78d6", "Dining room": "#eb6834", "Basement": "#1baf7a",
    "Children's room": "#eda100", "Master bedroom": "#e87ba4", "Living room": "#6250d6",
}
INK, MUTED, GRID = "#222222", "#666666", "#dddddd"


@dataclass(frozen=True)
class Mark:
    at: datetime
    label: str
    estimated: bool = False
    # Empty means every panel.
    rooms: tuple[str, ...] = ()
    until: datetime | None = None


def rooms() -> list:
    return [room for unit in report.UNITS for room in unit.rooms]


def pick_rooms(names: list[str]) -> list:
    """Match each name to one room by case-insensitive substring."""
    known = [r for r in rooms() if r.temp_query]
    if not names:
        return known
    picked = []
    for name in names:
        hits = [r for r in known if name.lower() in r.name.lower()]
        if len(hits) != 1:
            choices = ", ".join(r.name for r in known)
            raise ValueError(f"'{name}' matches {len(hits)} rooms with data; choose from: {choices}")
        picked.append(hits[0])
    return picked


CLOCK = re.compile(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", re.I)


def parse_when(s: str, day: date) -> datetime:
    """A clock time (7:10, 07:10, 7am, 7:10pm) falls on `day`; else an ISO datetime."""
    m = CLOCK.match(s.strip())
    if m and (m[2] or m[3]):
        hour, minute = int(m[1]), int(m[2] or 0)
        if m[3]:
            hour = hour % 12 + (12 if m[3].lower() == "pm" else 0)
        return datetime.combine(day, time(hour, minute), TZ)
    try:
        return datetime.fromisoformat(s.strip()).replace(tzinfo=TZ)
    except ValueError:
        raise ValueError(f"can't read time '{s}'; use 7:10, 7am, 7:10pm or 'YYYY-MM-DD HH:MM'") from None


def parse_mark(s: str, start: datetime) -> Mark:
    """[ROOM,ROOM@]TIME=LABEL. A clock time is the first at or after `start`."""
    when, sep, label = s.partition("=")
    if not sep or not label.strip():
        raise ValueError(f"--mark wants [ROOM@]TIME=LABEL, got '{s}'")
    names, _, when = when.rpartition("@")
    rooms = tuple(r.name for r in pick_rooms([n.strip() for n in names.split(",")])) if names else ()
    when = when.strip()
    estimated = when.startswith("~")
    at = parse_when(when.lstrip("~"), start.date())
    if at < start and CLOCK.match(when.lstrip("~")):
        at += timedelta(days=1)
    return Mark(at, label.strip(), estimated, rooms)


def parse_span(s: str, start: datetime) -> Mark:
    """FROM-TO=LABEL, shaded on every room panel."""
    times, sep, label = s.partition("=")
    a, dash, b = times.partition("-")
    if not (sep and dash and label.strip()):
        raise ValueError(f"--span wants FROM-TO=LABEL, got '{s}'")
    first = parse_mark(f"{a}=x", start)
    return Mark(first.at, label.strip(), first.estimated, until=parse_mark(f"{b}=x", first.at).at)


def stall_spans(temps: dict[str, list[tuple[float, float]]]) -> list[Mark]:
    """Each room's biggest fall, as an estimated span of no heat."""
    spans = []
    for name, pts in temps.items():
        drop = biggest_fall(pts) if pts else None
        if drop:
            (a, _), (b, _) = drop
            a, b = datetime.fromtimestamp(a, TZ), datetime.fromtimestamp(b, TZ)
            minutes = round((b - a).total_seconds() / 300) * 5
            spans.append(Mark(a, f"No heat about {a:%-I:%M}–{b:%-I:%M}\n({minutes} min)", True, (name,), b))
    return spans


def window(since: str | None, until: str | None, now: datetime) -> tuple[datetime, datetime]:
    end = parse_when(until, now.date()) if until else now
    start = parse_when(since, end.date()) if since else end - timedelta(hours=6)
    if start > end and since and CLOCK.match(since.strip()):
        start -= timedelta(days=1)
    if start >= end:
        raise ValueError(f"start {start:%Y-%m-%d %H:%M} is not before end {end:%Y-%m-%d %H:%M}")
    return start, end


def setpoint_changes(points: list[tuple[float, float]]) -> list[tuple[float, float, float]]:
    """(time, old °F, new °F) for each change in a setpoint series."""
    return [(t, a, b) for (_, a), (t, b) in zip(points, points[1:]) if round(a) != round(b)]


def summary(points: list[tuple[float, float]]) -> str:
    """Low, the biggest fall, and latest, so the shape is said in words."""
    fmt = lambda t: f"{datetime.fromtimestamp(t, TZ):%-I:%M}"
    lo_t, lo = min(points, key=lambda p: p[1])
    parts = [f"low {lo:.1f} at {fmt(lo_t)}"]
    drop = biggest_fall(points)
    if drop:
        (a_t, a), (b_t, b) = drop
        parts.append(f"fell {a:.1f}→{b:.1f} from {fmt(a_t)} to {fmt(b_t)}")
    parts.append(f"now {points[-1][1]:.1f} °F")
    return ", ".join(parts)


def biggest_fall(points: list[tuple[float, float]], at_least: float = 1.0, minutes: int = 20):
    """The largest drop from a peak to a later low, at least `at_least` °F over `minutes`.

    A drop of `at_least` within 5 minutes of leaving the peak is a head's
    warm burst on a thermostat, not a room cooling, so that peak is skipped.
    """
    best, peak, left, burst = None, points[0], points[0][0], False
    for p in points:
        if p[1] > peak[1]:
            peak, left, burst = p, p[0], False
        elif p[1] == peak[1]:
            left = p[0]
        elif peak[1] - p[1] >= at_least:
            burst = burst or p[0] - left < 5 * 60
            if (not burst and p[0] - peak[0] >= minutes * 60
                    and (best is None or peak[1] - p[1] > best[0][1] - best[1][1])):
                best = (peak, p)
    return best


def collect(picked: list, start: datetime, end: datetime) -> dict:
    step = report.step_seconds(start, end)
    f = lambda pts: [(t, report.c_to_f(v)) for t, v in pts]
    temps = {r.name: f(report.query_range(r.temp_query, start, end)) for r in picked}
    targets, zones = {}, {}
    for entity, label in ZONES.items():
        calls = report.query_range(f'hass_climate_action{{entity="{entity}",action="heating"}}', start, end)
        targets[entity] = f(report.query_range(f'hass_climate_target_temperature_celsius{{entity="{entity}"}}', start, end))
        zones[label] = {"spans": report.heating_spans(calls, step), "setpoints": setpoint_changes(targets[entity])}
    try:
        outdoor = report.outdoor(start, end)
    except (URLError, KeyError, ValueError):
        outdoor = []
    return {"temps": temps, "targets": targets, "zones": zones, "outdoor": outdoor}


def plot(data: dict, picked: list, marks: list[Mark], start: datetime, end: datetime,
         plain: bool, out: Path, setpoints: dict[str, float] | None = None, boiler: bool = True,
         outdoor: bool = True, overlay: bool = False, spans: list[Mark] | None = None) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MultipleLocator

    def local(ts: float) -> datetime:
        return datetime.fromtimestamp(ts, TZ)

    def draw_mark(ax, m: Mark, y: float, coords: str) -> None:
        """A line on `ax` and its label at height `y`."""
        style = (0, (1, 2)) if m.estimated else (0, (5, 3))
        text = f"{'about ' if m.estimated else ''}{m.at:%-I:%M} {m.label}"
        # Labels near the right edge go left of their line.
        right = (m.at - start) / (end - start) > 0.75
        ax.annotate(text, (m.at, y), xycoords=("data", coords), xytext=(-4 if right else 4, 0),
                    textcoords="offset points", ha="right" if right else "left",
                    va="center", fontsize=10, color=INK)
        return style

    setpoints = setpoints or {}
    zones = list(data["zones"].items()) if boiler else []
    shared = [m for m in marks if not m.rooms]
    # Shared mark labels get their own strip so they never cover data.
    lead = 1 if shared else 0
    out_x = [local(t) for t, _, _ in data["outdoor"]]
    out_f = [f for _, f, _ in data["outdoor"]]
    overlay = overlay and outdoor and bool(out_f)
    show_out = outdoor and bool(out_f) and not overlay
    heights = ([0.3 * len(shared)] * lead + [6 if overlay else 3] * len(picked) + [1.4] * show_out
               + ([0.6 * len(zones)] if zones else []))
    fig, axs = plt.subplots(len(heights), 1, figsize=(8, 1.15 * sum(heights) + 1.2), sharex=True,
                            gridspec_kw={"height_ratios": heights}, squeeze=False)
    axs = axs[:, 0]
    room_axs = axs[lead:lead + len(picked)]

    values = [v for pts in data["temps"].values() for _, v in pts]
    values += [setpoints[r.name] for r in picked if r.name in setpoints]
    values += out_f if overlay else []
    lo, hi = min(values, default=60), max(values, default=70)
    # Headroom for room mark labels above the data.
    per_room = max((sum(r.name in m.rooms for m in marks) for r in picked), default=0)
    top = hi + 0.9 + 0.9 * per_room
    for ax, room in zip(room_axs, picked):
        pts = data["temps"][room.name]
        title = room.name if plain else f"{room.name} ({room.source})"
        ax.set_ylim(lo - 0.7, top)
        ax.set_ylabel("°F", color=MUTED)
        ax.grid(axis="y", color=GRID, lw=0.6)
        if room.name in setpoints:
            ax.axhline(setpoints[room.name], color=INK, lw=1.2, ls=(0, (6, 3)))
            ax.annotate(f"head set to {setpoints[room.name]:.0f} °F", (1, setpoints[room.name]),
                        xycoords=("axes fraction", "data"), xytext=(-4, 4), textcoords="offset points",
                        ha="right", fontsize=10, color=INK)
        own = [m for m in marks if room.name in m.rooms]
        for i, m in enumerate(own):
            y = top - 0.45 - 0.9 * i
            style = draw_mark(ax, m, y, "data")
            ax.axvline(m.at, color=INK, lw=1.2, ls=style)
        if not pts:
            ax.set_title(title, loc="left", fontsize=12, color=INK)
            ax.text(0.5, 0.5, "no data", transform=ax.transAxes, ha="center", color=MUTED)
            continue
        ax.set_title(title if plain else f"{title}\n{summary(pts)}", loc="left", fontsize=12, color=INK)
        ax.plot([local(t) for t, _ in pts], [v for _, v in pts], color=COLORS.get(room.name, "#2a78d6"), lw=2)
        if overlay:
            ax.yaxis.set_major_locator(MultipleLocator(2))
            ax.plot(out_x, out_f, color="#888888", lw=1.5, marker="o", ms=3)
            ax.annotate(room.name, (local(pts[-1][0]), pts[-1][1]), xytext=(-4, -12), textcoords="offset points",
                        ha="right", fontsize=10, color=INK)
            ax.annotate("Outdoor", (out_x[-1], out_f[-1]), xytext=(-4, 8), textcoords="offset points",
                        ha="right", fontsize=10, color=MUTED)
        target = data["targets"].get(room.call_entity or "", []) if boiler else []
        if target:
            ax.step([local(t) for t, _ in target], [v for _, v in target], where="post",
                    color=MUTED, lw=1, ls=(0, (2, 2)))
            ax.annotate("boiler thermostat setpoint", (local(target[-1][0]), target[-1][1]), xytext=(-4, 4),
                        textcoords="offset points", ha="right", fontsize=9, color=MUTED)

    if show_out:
        out_ax = axs[lead + len(picked)]
        temps = out_f
        out_ax.plot(out_x, temps, color="#888888", lw=1.5, marker="o", ms=3)
        mid = (min(temps) + max(temps)) / 2
        out_ax.set_ylim(min(min(temps), mid - 3) - 0.5, max(max(temps), mid + 3) + 0.5)
        out_ax.set_ylabel("°F", color=MUTED)
        out_ax.grid(axis="y", color=GRID, lw=0.6)
        name = "Outdoor" if plain else "Outdoor (KFSO, Highgate airport, 6 mi away)"
        out_ax.set_title(f"{name}  ·  {min(temps):.0f}–{max(temps):.0f} °F", loc="left", fontsize=12, color=INK)

    if zones:
        zax = axs[-1]
        for row, (label, z) in enumerate(zones):
            y0, y1 = 1 - (row + 1) / len(zones), 1 - row / len(zones)
            for a, b in z["spans"]:
                zax.axvspan(local(a), local(b), ymin=y0 + 0.15 / len(zones), ymax=y1 - 0.15 / len(zones),
                            color="#c0392b", lw=0)
            for t, a, b in z["setpoints"]:
                zax.axvline(local(t), ymin=y0, ymax=y1, color=INK, lw=1)
                zax.annotate(f"setpoint {a:.0f}→{b:.0f} °F", (local(t), len(zones) - row - 0.5), xytext=(4, 0),
                             textcoords="offset points", va="center", fontsize=10, color=INK)
            if not z["spans"]:
                zax.text(0.01, len(zones) - row - 0.5, "did not fire", transform=zax.get_yaxis_transform(),
                         va="center", fontsize=10, color=MUTED)
        zax.set_ylim(0, len(zones))
        zax.set_yticks([len(zones) - r - 0.5 for r in range(len(zones))], [l for l, _ in zones], fontsize=10)
        zax.set_title("Oil boiler firing (red)", loc="left", fontsize=12, color=INK)
        zax.tick_params(axis="y", length=0)

    for sp in spans or []:
        for ax, room in zip(room_axs, picked):
            if sp.rooms and room.name not in sp.rooms:
                continue
            ax.axvspan(sp.at, sp.until, color="#c0392b", alpha=0.12, lw=0)
            ax.annotate(sp.label, ((sp.at + (sp.until - sp.at) / 2), 0.5), xycoords=("data", "axes fraction"),
                        ha="center", va="center", fontsize=11, color="#8e2a1f")

    for i, m in enumerate(shared):
        style = draw_mark(axs[0], m, len(shared) - i - 0.5, "data")
        axs[0].plot([m.at, m.at], [0, len(shared) - i - 0.5], color=INK, lw=1.2, ls=style)
        for ax in axs[lead:]:
            ax.axvline(m.at, color=INK, lw=1.2, ls=style)

    for ax in axs:
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    if lead:
        axs[0].set_ylim(0, len(shared))
        axs[0].axis("off")
    axs[-1].set_xlim(start, end)
    axs[-1].xaxis.set_major_formatter(mdates.DateFormatter("%-I:%M %p", tz=TZ))
    fig.suptitle(f"{start:%a %b %-d, %-I:%M %p} to {end:%-I:%M %p} (Eastern)",
                 x=0.02, ha="left", fontsize=12, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    fig.savefig(out, dpi=130)
    plt.close(fig)


def parse_setpoint(s: str) -> tuple[str, float]:
    name, sep, value = s.partition("=")
    try:
        return pick_rooms([name.strip()])[0].name, float(value)
    except ValueError:
        raise ValueError(f"--setpoint wants ROOM=°F, got '{s}'") from None


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("rooms", nargs="*", help="room names or parts of them (default: every room with data)")
    p.add_argument("--since", help="start: 6am, 6:00 or 'YYYY-MM-DD HH:MM' (default 6 hours before --until)")
    p.add_argument("--until", help="end, same forms (default now)")
    p.add_argument("--mark", action="append", default=[], help='an event line, "TIME=LABEL"; "ROOM@TIME=..." for one panel; "~TIME" for an estimate')
    p.add_argument("--setpoint", action="append", default=[], help='a head\'s setpoint, "ROOM=°F"; repeatable')
    p.add_argument("--no-boiler", action="store_true", help="leave out the boiler strip and thermostat setpoints")
    p.add_argument("--outdoor-on-chart", action="store_true", help="draw outdoor on each room's panel, not its own")
    p.add_argument("--no-outdoor", action="store_true", help="leave out the outdoor panel")
    p.add_argument("--span", action="append", default=[], help='a shaded stretch, "FROM-TO=LABEL"; repeatable')
    p.add_argument("--stall", action="store_true",
                   help="shade each room's biggest fall (1 °F or more) as an estimated stretch of no heat")
    p.add_argument("--share", action="store_true",
                   help="for the installer: --plain, --outdoor-on-chart and --no-boiler together")
    p.add_argument("--plain", action="store_true", help="room names only: no sensor types or summary (for sharing)")
    p.add_argument("--out", type=Path, default=Path("room-temps.png"), help="PNG path (default ./room-temps.png)")
    p.add_argument("--list", action="store_true", help="list rooms, their sensors and outdoor units, then exit")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.share:
        args.plain = args.outdoor_on_chart = args.no_boiler = True
    if args.list:
        for unit in report.UNITS:
            for r in unit.rooms:
                print(f"{r.name:<16} {r.source:<34} {unit.model} {unit.serial}{'' if r.temp_query else '  (no data)'}")
        return 0
    try:
        picked = pick_rooms(args.rooms)
        start, end = window(args.since, args.until, datetime.now(TZ))
        marks = [parse_mark(m, start) for m in args.mark]
        setpoints = dict(parse_setpoint(s) for s in args.setpoint)
        spans = [parse_span(s, start) for s in args.span]
    except ValueError as e:
        print(f"room-temps: {e}", file=sys.stderr)
        return 2
    for m in marks:
        if not start <= m.at <= end:
            print(f"room-temps: mark '{m.label}' at {m.at:%Y-%m-%d %H:%M} is outside the window", file=sys.stderr)
    try:
        data = collect(picked, start, end)
    except (URLError, RuntimeError) as e:
        print(f"room-temps: could not fetch data: {e}", file=sys.stderr)
        return 1
    if args.stall:
        spans += stall_spans(data["temps"])
    plot(data, picked, marks, start, end, args.plain, args.out, setpoints, not args.no_boiler,
         not args.no_outdoor, args.outdoor_on_chart, spans)
    print(args.out.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
