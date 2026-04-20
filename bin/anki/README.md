# bin/anki/

Utility scripts for managing [Anki](https://apps.ankiweb.net/) — a spaced repetition flashcard app.

These scripts complement the `/anki` Claude Code skill used in `~/Git/notes` (a private Obsidian vault) to create and manage flashcards from vault notes.

## Scripts

| Script | Description |
|--------|-------------|
| `list-anki-decks.py` | Print all decks with card counts in a tree view |
| `backup-anki.py` | Snapshot the Anki database (fails loudly if Anki is open) |
| `is-anki-running.py` | Exit 0 if Anki is running, 1 if not (used by other scripts) |
| `toggle-anki-card-order.py` | Toggle new card order between oldest-first and newest-first |

## Usage

All scripts use [PEP 723](https://peps.python.org/pep-0723/) inline metadata and are run with `uv`:

```bash
uv run list-anki-decks.py
uv run backup-anki.py
uv run toggle-anki-card-order.py
```

## Dependencies

- Scripts that read/write the Anki database require the `anki` Python package (auto-installed by `uv`).
- `is-anki-running.py` has no external dependencies.
- **Anki must be closed** before running any script that writes to the database.

## Safety

`backup-anki.py` and `toggle-anki-card-order.py` automatically check whether Anki is running and create a timestamped backup before making any changes.
