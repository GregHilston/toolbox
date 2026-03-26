# bin

Standalone utility scripts, available on `$PATH` via `$TOOLBOX_HOME/bin` in `.zshrc`.

## Adding a new script

1. Create the script in this directory
2. Make it executable (`chmod +x`)
3. Optionally add a convenience alias in `dot/zsh/.zshrc`

Bash scripts use [unofficial strict mode](http://redsymbol.net/articles/unofficial-bash-strict-mode/). Python scripts use [PEP 723](https://peps.python.org/pep-0723/) inline metadata and are run with `uv run`.
