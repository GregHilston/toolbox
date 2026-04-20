#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "anki",
# ]
# ///

# Lists all Anki decks with card counts in a hierarchical tree view.

import logging
import os
import sys
from pathlib import Path

from anki.collection import Collection

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

COLLECTION_PATH = Path(
    "~/Library/Application Support/Anki2/User 1/collection.anki2"
).expanduser()


def main() -> None:
    if not COLLECTION_PATH.exists():
        log.error(f"Collection not found at: {COLLECTION_PATH}")
        sys.exit(1)

    col = Collection(str(COLLECTION_PATH))

    try:
        all_decks = col.decks.all_names_and_ids()
        sorted_decks = sorted(all_decks, key=lambda x: x.name)

        print("\nAnki Deck Structure")
        print("=" * 60)

        total_cards = 0
        for deck_info in sorted_decks:
            name = deck_info.name
            deck_id = deck_info.id
            count = col.decks.card_count(deck_id, include_subdecks=False)
            total_cards += count

            depth = name.count("::")
            indent = "  " * depth
            display_name = name.split("::")[-1] if "::" in name else name
            count_str = f"  ({count} cards)" if count > 0 else ""

            print(f"{indent}• {display_name}{count_str}")

        print("=" * 60)
        print(f"Total: {total_cards} cards across {len(sorted_decks)} decks\n")
    finally:
        col.close()


if __name__ == "__main__":
    main()
