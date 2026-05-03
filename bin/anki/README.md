# bin/anki/

Utility scripts for managing [Anki](https://apps.ankiweb.net/) — a spaced repetition flashcard app.

These scripts complement the `/anki` Claude Code skill used in `~/Git/notes` (a private Obsidian vault) to create and manage flashcards from vault notes.

## Scripts

| Script | Description |
|--------|-------------|
| `_audit-card-formatting.py` | Scan collection for markdown/formatting issues; run periodically to catch regressions |
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

## Card Creation & Formatting Best Practices

When creating new cards (via Claude Code or manual entry), follow these rules:

### HTML, Not Markdown
Anki renders **HTML**, not Markdown. Never use raw markdown syntax:
- ❌ `**bold**` → ✅ `<b>bold</b>`
- ❌ `` `code` `` → ✅ `<code>code</code>`
- ❌ `# Header` → ✅ `<h3>Header</h3>`
- ❌ `- bullet` → ✅ `<ul><li>bullet</li></ul>`

### Code Formatting (Prism.js Syntax Highlighting)

**Use `<pre><code class="language-X">` blocks** for multi-keyword statements or standalone code answers:
- SQL with keywords: `<pre><code class="language-sql">FROM Restaurants r JOIN Orders o ON r.id = o.restaurant_id</code></pre>`
- Python patterns: `<pre><code class="language-python">[[] for _ in range(n)]</code></pre>`

**Use inline `<code>` tags** for short identifiers and single terms:
- Column names: `<code>COUNT(DISTINCT o.id)</code>`
- Keywords: `<code>reverse=True</code>`
- Inline references: "Use `<code>PRAGMA table_info()</code>` to inspect columns"

**Always specify the language class** on pre/code blocks: `language-sql`, `language-python`, etc. This enables syntax highlighting in both Anki and AnkiDroid.

### Audit for Regressions
After bulk card creation or edits, run the audit script to check for formatting issues:
```bash
uv run _audit-card-formatting.py
```

See `~/Git/notes/CLAUDE.md` for the complete formatting guide.
