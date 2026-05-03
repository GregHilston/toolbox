#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["anki"]
# ///
"""
Audit Anki cards for common formatting issues.

Detects:
- Raw markdown (bold **text**, backticks `code`, headers #, bullets -)
- Code blocks without proper <pre><code> wrapping
- Escaped HTML entities that might be unintended

Excludes content inside <pre> and <code> blocks to avoid false positives.
"""

from anki.collection import Collection
import os
import re


def audit_card_formatting():
    col_path = os.path.expanduser('~/Library/Application Support/Anki2/User 1/collection.anki2')
    col = Collection(col_path)

    note_ids = col.find_notes("")
    print(f"Total notes: {len(note_ids)}\n")

    deck_map = {}
    for deck_info in col.decks.all_names_and_ids():
        deck_map[deck_info.id] = deck_info.name

    issues = {
        "raw_markdown_bold": [],
        "raw_markdown_backtick": [],
        "raw_markdown_header": [],
        "raw_markdown_bullets": [],
        "escaped_html": [],
    }

    seen_ids = set()

    for note_id in note_ids:
        note = col.get_note(note_id)
        cards = note.cards()
        deck_name = "Unknown"
        if cards:
            deck_id = cards[0].did
            deck_name = deck_map.get(deck_id, "Unknown")

        front = note.fields[0] if note.fields else ""
        back = note.fields[1] if len(note.fields) > 1 else ""

        card_info = {
            "id": note_id,
            "deck": deck_name,
            "front": front[:200],
            "back": back[:400],
        }

        # Strip code blocks from content to avoid false positives
        stripped = re.sub(r'<pre[^>]*>.*?</pre>', '', back + "\n" + front, flags=re.DOTALL)
        stripped = re.sub(r'<code[^>]*>.*?</code>', '', stripped, flags=re.DOTALL)

        card_issues = []

        # Check for raw markdown bold
        if re.search(r'\*\*[^\*\n]+\*\*', stripped):
            issues["raw_markdown_bold"].append(card_info)
            card_issues.append("bold")

        # Check for backtick code
        if '`' in stripped:
            issues["raw_markdown_backtick"].append(card_info)
            card_issues.append("backtick")

        # Check for markdown headers
        if re.search(r'^#{1,6}\s', stripped, re.MULTILINE):
            issues["raw_markdown_header"].append(card_info)
            card_issues.append("header")

        # Check for markdown bullets
        if re.search(r'^[-*]\s', stripped, re.MULTILINE):
            issues["raw_markdown_bullets"].append(card_info)
            card_issues.append("bullets")

        # Check for escaped HTML entities (for information, not necessarily an issue)
        if re.search(r'&lt;|&gt;|&amp;|&quot;', back + front):
            issues["escaped_html"].append(card_info)
            card_issues.append("escaped_html")

        if card_issues:
            seen_ids.add(note_id)

    print(f"Total notes with at least one formatting issue: {len(seen_ids)}\n")
    print(f"=== ISSUE COUNTS ===")
    for issue_type, cards in issues.items():
        if cards:
            print(f"  {issue_type}: {len(cards)}")

    print(f"\n=== EXAMPLES PER CATEGORY ===")
    for issue_type, cards in issues.items():
        if cards:
            print(f"\n{'='*60}")
            print(f"ISSUE: {issue_type} ({len(cards)} cards)")
            print(f"{'='*60}")
            for c in cards[:3]:
                print(f"  Deck: {c['deck']}")
                print(f"  Front: {repr(c['front'][:120])}")
                print(f"  Back:  {repr(c['back'][:250])}")
                print()

    col.close()


if __name__ == "__main__":
    audit_card_formatting()
