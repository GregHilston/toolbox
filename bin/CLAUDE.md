# bin/

Standalone utility scripts. All scripts are on `$PATH` via `$TOOLBOX_HOME/bin` in `.zshrc`.

## Conventions

### Bash strict mode

All bash scripts must use the [unofficial bash strict mode](http://redsymbol.net/articles/unofficial-bash-strict-mode/):

```bash
#!/bin/bash
set -euo pipefail
IFS=$'\n\t'
```

This causes scripts to fail fast on errors (`set -e`), undefined variables (`set -u`), and pipe failures (`set -o pipefail`). The `IFS` change makes word splitting behave sanely with filenames containing spaces.

### Script structure

- Kebab-case filenames for executables (`.sh`/`.py`); use snake_case only for
  Python modules that other scripts `import` (hyphens aren't importable) — e.g.
  `fetch_hn.py` / `_thread_converters.py`, imported by `fetch-thread.py`
- A one-line comment near the top explaining what the script does
- Bash scripts: strict mode header (see above)
- Python scripts: shebang + [PEP 723](https://peps.python.org/pep-0723/) inline metadata:

```python
#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["requests"]
# ///
```

The shebang lets you run `script.py` directly instead of `uv run script.py`.
Without it, the shell interprets the Python code as shell commands.

### Secrets

Secrets from 1Password are auto-loaded into every shell session via `.zshrc`
(sourced from `nixos/secrets/.env`). Scripts can read them with `os.environ.get()`
or `$VAR` — no manual sourcing needed.

If a secret is missing, the user needs to run `just secrets` in `nixos/` and open
a new terminal.

### Adding a new script

1. Create the script in this directory (or a subdirectory for grouped tools)
2. Make it executable (`chmod +x`)
3. Optionally add a convenience alias in `dot/zsh/.zshrc`

### Tests

Tests for these scripts live in `tests/` **at the repo root**, not here — the
recursive `$PATH` glob in `.zshrc` would otherwise put a test directory on
`$PATH`. Run them with `just test` (which also runs the pi extension suite), or
`cd tests && python3 -m unittest discover`.

They are stdlib `unittest`, no dependencies. Because executables here are
kebab-case and so are not importable by name, `tests/_loader.py` imports them by
path; use it rather than renaming a script or adding a wrapper module.

Two things there are worth copying if you write a script with moving parts:

- `tests/fake_pi.py` is a stand-in for `pi --mode rpc` that misbehaves on
  request — no acknowledgement, no settle, floods stderr, stops reading stdin.
  `pi-rpc.py` selects it with `PI_RPC_BIN`. Every serious defect review found in
  that script was in thread/subprocess/socket interaction, invisible to unit
  tests of its pure functions and trivially reachable this way. The lifecycle
  tests spawn processes and bind sockets, so the suite takes about a minute.
- `tests/fixtures/real-pi-session.jsonl` is a captured real pi run, replayed
  through the narrator. The hand-written fixtures elsewhere are self-consistent
  and would all be wrong together if pi's schema moved; this one is the check
  that notices.

## Subdirectories

Subdirectories group related scripts and are added to `$PATH` automatically via the recursive glob in `.zshrc` — no manual PATH update needed when adding a new subdirectory. Explore `bin/` to see what's available.
