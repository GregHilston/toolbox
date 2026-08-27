"""Load a hyphenated `bin/` script as an importable module.

`bin/` names executables in kebab-case, which is not a legal module name, and
the repo reserves snake_case there for modules other scripts import. Tests are
the one other caller, so they load by path rather than forcing a rename or a
wrapper module that exists only for testing.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin"


def load(script: str) -> types.ModuleType:
    """Import `bin/<script>` under a sanitised module name."""
    path = BIN / script
    name = "_" + path.stem.replace("-", "_")
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - a broken checkout
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
