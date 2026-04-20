#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

# Backs up the Anki collection database. Fails loudly if Anki is running.

import logging
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

COLLECTION_PATH = Path(
    "~/Library/Application Support/Anki2/User 1/collection.anki2"
).expanduser()
IS_RUNNING_SCRIPT = Path(__file__).parent / "is-anki-running.py"


def main() -> None:
    log.info("Checking if Anki is running...")
    result = subprocess.run(["uv", "run", str(IS_RUNNING_SCRIPT)], capture_output=True)

    if result.returncode == 0:
        log.error("Anki is currently open — close it before backing up the database.")
        sys.exit(1)

    log.info("Anki is not running. Proceeding with backup.")

    if not COLLECTION_PATH.exists():
        log.error(f"Collection not found at: {COLLECTION_PATH}")
        sys.exit(1)

    backup_name = f"collection.anki2.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    backup_path = COLLECTION_PATH.parent / backup_name
    shutil.copy2(COLLECTION_PATH, backup_path)

    log.info(f"Backed up to: {backup_path}")


if __name__ == "__main__":
    main()
