#!/usr/bin/env python3
"""Tiny script proving the flake's Python + packages are on PATH.

`requests` is imported (not called) so this runs offline — if the import
succeeds, the dev shell loaded the flake's Python environment correctly.
"""

import sys

import requests  # provided by the flake, not the system Python


def main() -> None:
    print(f"Hello from Python {sys.version.split()[0]}")
    print(f"requests {requests.__version__} is importable — the dev shell works.")


if __name__ == "__main__":
    main()
