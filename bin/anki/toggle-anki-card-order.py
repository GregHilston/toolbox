#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "anki",
# ]
# ///

# Toggles the Anki new card gather priority between oldest-first (default) and newest-first.

import logging
import subprocess
import sys
from pathlib import Path

from anki.collection import Collection

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

COLLECTION_PATH = Path(
    "~/Library/Application Support/Anki2/User 1/collection.anki2"
).expanduser()
BACKUP_SCRIPT = Path(__file__).parent / "backup-anki.py"

PRIORITY_LABELS = {
    0: "Deck order — oldest first (default)",
    4: "Lowest position — oldest first",
    5: "Highest position — newest first",
}

# Any value not in this map gets flipped to newest-first
TOGGLE_MAP = {
    5: 0,  # newest-first → back to default (oldest first)
    0: 5,  # default       → newest-first
    4: 5,  # lowest pos    → newest-first
}


def main() -> None:
    log.info("Running backup before making changes...")
    result = subprocess.run(["uv", "run", str(BACKUP_SCRIPT)])
    if result.returncode != 0:
        log.error("Backup failed — aborting toggle.")
        sys.exit(1)

    log.info("Opening Anki collection...")
    col = Collection(str(COLLECTION_PATH))

    try:
        conf = col.decks.get_config(1)  # id=1 is the Default deck config
        current = conf["newGatherPriority"]
        current_label = PRIORITY_LABELS.get(current, f"Unknown ({current})")

        new_val = TOGGLE_MAP.get(current, 5)
        new_label = PRIORITY_LABELS.get(new_val, f"Unknown ({new_val})")

        log.info(f"Current order : {current_label}")
        log.info(f"Switching to  : {new_label}")

        conf["newGatherPriority"] = new_val
        col.decks.update_config(conf)

        log.info("Done. Reopen Anki for the change to take effect.")
    finally:
        col.close()


if __name__ == "__main__":
    main()
