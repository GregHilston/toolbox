#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

# Exits 0 if the Anki application is currently running, 1 if not.

import logging
import subprocess
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)


def is_anki_running() -> bool:
    result = subprocess.run(["pgrep", "-x", "Anki"], capture_output=True)
    return result.returncode == 0


def main() -> None:
    if is_anki_running():
        log.info("Anki is currently running.")
        sys.exit(0)
    else:
        log.info("Anki is not running.")
        sys.exit(1)


if __name__ == "__main__":
    main()
