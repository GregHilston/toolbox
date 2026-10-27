---
name: room-temps
description: Chart the house's room temperatures over a few hours as a PNG, with events marked (heads turned on, setpoint changed) and oil boiler firing shown. Use when Greg asks to graph, chart or show room temperatures, a mini-split, head or heat pump not heating, a room going cold, or wants a picture for the installer (Phil).
license: MIT
---

# Room temperatures

One command, already on `PATH`. Run it in your shell (the `terminal` tool in
Hermes, Bash in Claude Code, `bash` in pi) exactly as shown: no `python3` in
front and no directory. It is not a tool itself.

```bash
room-temps.py --list                                      # rooms, sensors, outdoor units
room-temps.py guest dining basement --since 6am --out /tmp/rooms.png
room-temps.py basement --since "2026-10-27 06:00" --until "2026-10-27 11:00" --out /tmp/rooms.png
room-temps.py guest dining --since 6am --mark "7:10=Heads on" --mark "~7:35=Basement head on" --out /tmp/rooms.png
room-temps.py guest dining basement --since 6am --plain --out /tmp/rooms.png
```

It prints the PNG's absolute path; show or send that file. Always pass `--out`
with an absolute path.

- **Rooms:** any part of a room's name, so `guest` is the guest room. No rooms
  means every room with data. A bad name exits 2 and lists the choices.
- **Times are Eastern.** `6am`, `6:00` or `YYYY-MM-DD HH:MM`. A clock time is
  today, or yesterday if it hasn't happened yet. "This morning" means
  `--since 6am`. Without `--since` the chart covers the last 6 hours.
- **`--mark "TIME=LABEL"`** draws an event line. Ask Greg when he did something;
  if you read a time off the chart instead, put `~` before it (`~7:35=...`), so
  it is drawn dotted and labelled "about". Put rooms first to draw it on
  their panels only: `--mark "guest,dining@7:09=Head on"`. Use that when the
  event concerns some rooms, so others' panels stay clean.
- **`--setpoint "basement=70"`** draws what a head is set to. Ask Greg; HA
  can't read the heads. A room that peaks below its setpoint and then falls
  is the clearest sign of a head that stopped heating.
- **`--plain`** for anything going to the installer: room names only, no
  sensor types. Add `--no-boiler` when no room shown is on a boiler zone
  (the basement isn't). `--outdoor-on-chart` draws outdoor on the room's own
  graph, which Greg prefers for a one-room chart; `--no-outdoor` drops it.
- **Show the decline.** If a room is still rising at the end, say so, and offer
  to re-run later with a later `--until`.

## Reading the chart

- Each room sensor stands in for the head in that room; the heads can't be
  read. The dining room and master bedroom readings come from their Honeywell
  T6 Pro thermostats and move in whole degrees.
- **The T6 Pros run the oil boiler.** Dining room is the 1st floor zone, master
  bedroom the 2nd. The bottom strip shows each zone firing and any setpoint
  change, and the setpoint is drawn dashed on that room's panel. A rise while
  the boiler fired is not the head's.
- A head blowing on the dining room thermostat lifts its reading for a few
  minutes when it starts.
- Outdoor is measured at the Highgate airport station (KFSO), 6 mi away,
  about every 20 minutes.
- The living room has no sensor; `--list` marks it "no data".

For the setup and what the installer has asked for, read the vault note
`~/Git/notes/llm/heat-pump-temperature-tracking.md`. For a multi-day PDF and
CSV per outdoor unit, use `heat-pump-report.py --days 7` instead.

Don't use Grafana screenshots or ad-hoc Prometheus queries for this: Grafana
has no image renderer, and this script already maps rooms to sensors.
