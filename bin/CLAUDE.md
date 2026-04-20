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

- Kebab-case filenames with `.sh` or `.py` extension
- A one-line comment near the top explaining what the script does
- Bash scripts: strict mode header (see above)
- Python scripts: [PEP 723](https://peps.python.org/pep-0723/) inline metadata so they can be run with `uv run <script>.py` with no separate requirements file

### Adding a new script

1. Create the script in this directory (or a subdirectory for grouped tools)
2. Make it executable (`chmod +x`)
3. Optionally add a convenience alias in `dot/zsh/.zshrc`

## Subdirectories

Subdirectories group related scripts and are added to `$PATH` automatically via the recursive glob in `.zshrc` — no manual PATH update needed when adding a new subdirectory. Explore `bin/` to see what's available.
