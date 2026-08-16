"""
oMLX API key loading, shared by every script in this directory.

Order: $OMLX_API_KEY, then a gitignored `omlx_key` file beside these scripts.
The file is listed in dot/omlx/.gitignore and must never be committed — every
other secret in this repo goes through 1Password / `op inject`, and this is the
one runtime credential that does not.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_KEY_FILE = os.path.join(_HERE, "omlx_key")

_HINT = """No oMLX API key found.

Either export it:
    export OMLX_API_KEY=...

or write it to {path} (gitignored):
    python3 -c "import json, os; print(json.load(
        open(os.path.expanduser('~/.omlx/settings.json')))['auth']['api_key'])" > {path}
"""


def load_key():
    key = os.environ.get("OMLX_API_KEY")
    if key and key.strip():
        return key.strip()
    try:
        with open(_KEY_FILE) as fh:
            key = fh.read().strip()
    except FileNotFoundError:
        sys.exit(_HINT.format(path=_KEY_FILE))
    if not key:
        sys.exit(_HINT.format(path=_KEY_FILE))
    return key
