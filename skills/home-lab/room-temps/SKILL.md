---
name: room-temps
description: Chart the house's room temperatures over a few hours as a PNG, with when heads went on, when heat stopped, the head setpoints, outdoor temperature and oil boiler firing. Use when Greg asks to graph, chart or show room temperatures, a mini-split, head or heat pump not heating or stalling, a room going cold, or wants a chart for the installer (Phil) or for his records.
license: MIT
---

# Room temperatures

One command, already on `PATH`. Run it in your shell (the `terminal` tool in
Hermes, Bash in Claude Code, `bash` in pi) exactly as shown: no `python3` in
front and no directory. It is not a tool itself.

## Ask Greg first

The heads can't be read, so these facts come only from Greg. Ask for any he
hasn't given:

- which rooms, and the window (default: since he turned the heads on);
- when each head went on, and anything he saw (heat stopped, heat back);
- what each head is set to.

## For Phil, or anyone outside the house

```bash
room-temps.py basement --since 6:30am --share --stall --setpoint basement=70 \
  --mark "7:33=Basement head on" --mark "9:34=Heat noticed again" \
  --out ~/Desktop/basement-for-phil.png
```

`--share` strips the technical detail: room names only, with no sensor types,
summaries or boiler strip, and outdoor on the same graph with a tick every
2 °F. `--stall` shades the room's biggest fall as "No heat about 8:08–9:33
(85 min)". One room per chart reads best; Greg chose a single basement chart
on 2026-10-27.

## For Greg's records

```bash
room-temps.py guest dining basement --since 6am --stall \
  --setpoint guest=72 --setpoint dining=71 --setpoint basement=70 \
  --mark "guest,dining@7:09=Head on" --mark "basement@7:33=Head on" \
  --out ~/Git/notes/attachments/YYYY-MM-DD-heat-pumps-all-rooms.png
```

One panel per room, with its sensor type and a summary (low, biggest fall,
latest), outdoor in its own panel, and the boiler zones firing at the bottom.
Embed it in that day's entry under "Observed by Greg" in
`~/Git/notes/llm/heat-pump-temperature-tracking.md`, and log there what Greg
saw. Then commit the notes.

## Options

- **Rooms:** any part of a name (`guest`, `basement`). `room-temps.py --list`
  shows them all. The living room has no sensor.
- **Times are Eastern:** `6am`, `6:00` or `YYYY-MM-DD HH:MM`. A clock time is
  today, or yesterday if it hasn't happened yet. `--until` defaults to now.
- **`--mark "TIME=LABEL"`** draws a dashed line.
  - Put rooms first (`"guest,dining@7:09=Head on"`) to draw it on those
    panels only.
  - Put `~` before a time you read off the chart rather than one Greg saw
    (`"~8:08=Heat stopped"`). It's drawn dotted and labelled "about".
- **`--setpoint ROOM=°F`** draws what a head is set to.
- **`--stall`** finds a fall of at least 1 °F lasting 20 minutes or more, and
  ignores a head's brief warm burst on a thermostat. It misses a flat stretch
  with no heat; shade that by hand with `--span "7:16-8:05=No heat"`.
- `--plain`, `--outdoor-on-chart`, `--no-outdoor` and `--no-boiler` are the
  parts of `--share`, for mixing by hand.

It prints the PNG's absolute path. Look at the image before sending it on.

## Reading the chart

- **A head that stopped heating:** the room peaks below the head's setpoint,
  then falls. Stopping 1–2 °F under setpoint is normal: the head reads its own
  sensor near the ceiling.
- **The thermostats:** the dining room and master bedroom readings come from
  Honeywell T6 Pro thermostats, in whole degrees. They also run the oil boiler,
  dining the 1st floor zone and master bedroom the 2nd. A rise while the
  boiler fired isn't the head's.
- **Outdoor** is measured at the Highgate airport station (KFSO), 6 mi away,
  about every 20 minutes. The newest hour may not be published yet.
- **Defrost** costs 10–25 minutes of heat at most; longer stalls are the fault
  being documented. Background and sources:
  `~/Git/notes/llm/heat-pump-temperature-tracking.md` and
  `~/Git/notes/llm/mitsubishi-heat-pump-failure-research.md`.

For a multi-day PDF and CSV per outdoor unit, use `heat-pump-report.py --days 7`.
Don't use Grafana screenshots or ad-hoc Prometheus queries for this: Grafana
has no image renderer, and this script already maps rooms to sensors.
