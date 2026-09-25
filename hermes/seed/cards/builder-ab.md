Childcare capacity by county

Your working directory is the project root. Build a small Python package there
following ENGINEERING.md. It describes the whole project; build only the one
adapter this card needs. pyproject.toml is already correct: do not edit it.

The only input is data/raw/vt-childcare-providers.json: 1,048 licensed Vermont
child care providers. It is 1.3 MB, so do not read it into the conversation.
Inspect it with `jq '.[0]'` and `jq 'length'`, and have your code stream it.
Every value in the file is a string. The fields you need are `county`,
`total_licensed_capacity` (digits, e.g. "30") and `current_stars_level`
("1 Star" to "5 Star", or "Not Rated").

Add a subcommand to the `vt-smb` console script (`vt_smb.cli:main`, a click
group):

    vt-smb childcare-capacity [--min-stars N] [--input PATH]

It prints CSV to stdout: a header `county,providers,capacity`, then one row per
county with the number of providers and the sum of their total licensed
capacity. Sort by capacity descending, then county name ascending. `--input`
defaults to data/raw/vt-childcare-providers.json. `--min-stars N` keeps only
providers rated N stars or more; "Not Rated" never passes the filter, but
without the flag every provider counts.

Structure, per ENGINEERING.md: the parsing and aggregation in domain/ with no
I/O imports, a frozen DTO and mapper in the adapter, the adapter's mapper tested
against a recorded fixture of a few real rows, and domain tests for the sort
order, the star filter and "Not Rated".

Work offline. Do not fetch anything.

DONE WHEN all of these hold:
1. `uv run pytest` passes with zero failures
2. `uv run vt-smb childcare-capacity` exits 0 and prints 15 lines
3. `uv run vt-smb childcare-capacity --min-stars 4` exits 0
4. pyproject.toml is unchanged
