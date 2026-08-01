#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Audit `<table class="recipe-table">` blocks in the notes vault.

Checks the failure modes that are invisible until Obsidian renders the note:
  - rowspan/colspan arithmetic that doesn't produce a rectangular grid
  - blank lines inside the HTML block (ends it; Obsidian resumes Markdown parsing)
  - inline style attributes (styling must come from the CSS snippet)
  - unknown cell classes
  - raw Markdown (**bold**, `code`) inside cells, which Obsidian will not render
  - unclosed / mismatched table tags

Usage: python3 audit-recipe-tables.py [vault_dir]
"""
import glob
import os
import re
import sys
from html.parser import HTMLParser

VAULT = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Git/notes")
ALLOWED_CLASSES = {"op", "prep", "note", "recipe-table"}


class TableParser(HTMLParser):
    """Collect (colspan, rowspan, attrs) per row for one <table> block."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.rows = []
        self.problems = []
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "tr":
            self.rows.append([])
        elif tag in ("td", "th"):
            if not self.rows:
                self.problems.append("cell outside any <tr>")
                self.rows.append([])
            try:
                cs = int(a.get("colspan", 1))
                rs = int(a.get("rowspan", 1))
            except ValueError:
                self.problems.append(f"non-integer span: {a}")
                cs = rs = 1
            if "style" in a:
                self.problems.append("inline style attribute (use the CSS snippet)")
            for cls in a.get("class", "").split():
                if cls not in ALLOWED_CLASSES:
                    self.problems.append(f"unknown class {cls!r}")
            self.rows[-1].append((cs, rs))


def grid_width(rows):
    """Lay cells out on a grid honouring spans; return per-row occupied widths."""
    occupied = set()
    widths = []
    for r, row in enumerate(rows):
        c = 0
        for cs, rs in row:
            while (r, c) in occupied:
                c += 1
            for dr in range(rs):
                for dc in range(cs):
                    occupied.add((r + dr, c + dc))
            c += cs
        widths.append(max((col for (rr, col) in occupied if rr == r), default=-1) + 1)
    # rows created purely by rowspan carry-over past the last <tr>
    overflow = max((rr for (rr, _) in occupied), default=-1) + 1 - len(rows)
    return widths, overflow


def audit(path):
    text = open(path, encoding="utf-8").read()
    issues = []
    blocks = re.findall(
        r'<table class="recipe-table">.*?</table>', text, re.DOTALL
    )
    n_open = text.count("<table")
    n_close = text.count("</table>")
    if n_open != n_close:
        issues.append(f"mismatched table tags: {n_open} <table>, {n_close} </table>")
    if n_open and not blocks:
        issues.append('has <table> but not class="recipe-table"')

    for i, block in enumerate(blocks, 1):
        tag = f"table {i}" if len(blocks) > 1 else "table"
        if re.search(r"\n[ \t]*\n", block):
            issues.append(f"{tag}: BLANK LINE inside the HTML block")
        if re.search(r"\*\*|(?<!<)`", block):
            issues.append(f"{tag}: raw Markdown in a cell (Obsidian renders HTML only)")

        p = TableParser()
        p.feed(block)
        for prob in p.problems:
            issues.append(f"{tag}: {prob}")
        if not p.rows:
            issues.append(f"{tag}: no rows parsed")
            continue

        widths, overflow = grid_width(p.rows)
        if overflow > 0:
            issues.append(
                f"{tag}: rowspan overruns the end of the table by {overflow} row(s)"
            )
        distinct = sorted(set(widths))
        if len(distinct) > 1:
            bad = [
                f"row {r + 1}={w}" for r, w in enumerate(widths) if w != max(widths)
            ]
            issues.append(
                f"{tag}: RAGGED GRID — widths {distinct}, expected {max(widths)} "
                f"({', '.join(bad[:6])})"
            )

    # placement: every table must sit directly under an "At a Glance" heading.
    # A note title may precede it, and multi-recipe notes may repeat the pattern.
    # Sub-headings are fine (## At a Glance > ### Sauce), so walk the hierarchy:
    # find the last "At a Glance" heading, then confirm no heading at the same or
    # higher level closed the section before the table starts.
    for i, m in enumerate(
        re.finditer(r'<table class="recipe-table">', text), 1
    ):
        tag = f"table {i}" if len(blocks) > 1 else "table"
        headings = [
            (mm.start(), len(mm.group(1)), mm.group(2).strip())
            for mm in re.finditer(r"^(#{1,6}) +(.*)$", text[: m.start()], re.M)
        ]
        glance = next(
            (h for h in reversed(headings) if "at a glance" in h[2].lower()), None
        )
        if glance is None:
            issues.append(f"{tag}: no 'At a Glance' heading above it")
            continue
        closed = [h for h in headings if h[0] > glance[0] and h[1] <= glance[1]]
        if closed:
            issues.append(
                f"{tag}: sits outside its 'At a Glance' section "
                f"(closed by {closed[0][2]!r})"
            )

    return blocks, issues


def main():
    files = sorted(glob.glob(os.path.join(VAULT, "recipe-*.md")))
    with_table = bad = 0
    for path in files:
        blocks, issues = audit(path)
        if blocks:
            with_table += 1
        if issues:
            bad += 1
            print(f"\n{os.path.basename(path)}")
            for msg in issues:
                print(f"  - {msg}")

    print(
        f"\n{'=' * 60}\n{len(files)} recipe files | {with_table} with a table | "
        f"{bad} with issues"
    )
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
