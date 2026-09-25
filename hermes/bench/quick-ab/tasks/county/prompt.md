data/providers.json holds 1,048 Vermont child care providers. Every value is a
string: `county`, `total_licensed_capacity` (digits) and `current_stars_level`
("1 Star" to "5 Star", or "Not Rated").

Write src/cc/stats.py with:

    def capacity_by_county(path, min_stars=None) -> list[tuple[str, int, int]]

returning (county, number_of_providers, total_capacity) per county, sorted by
total_capacity descending, then county ascending. With min_stars=N keep only
providers rated N stars or more; "Not Rated" never passes, but with
min_stars=None every provider counts.

Also add a click command in src/cc/cli.py (a group named `main`) with a
subcommand `capacity` taking `--min-stars N` that prints `county,providers,capacity`
then one line per county. Add tests under tests/. pyproject.toml is already
correct: do not edit it. You are done when `uv run pytest` passes.
