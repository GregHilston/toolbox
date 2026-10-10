#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Regenerate a vault's _vault-index.md, _vault-tags.md and _vault-cache.json.

Summaries come from an OpenAI-compatible endpoint, cached by content hash.
Tag overrides: `[tag-descriptions]` in `<vault>/.notes-index.toml`.
Exit codes: 0 ok, 1 any summary or tag failed, 2 bad or missing key.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tomllib
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path, PurePosixPath

DEFAULT_BASE_URL = "https://llm.grehg2.xyz/v1"
DEFAULT_MODEL = "local-small"
END_USER = "notes-index"
UNAVAILABLE = "(summary unavailable)"
MARKER = "<!-- managed by notes-index: do not edit manually — regenerate with `notes-index.py` -->"

INDEX_FILE = "_vault-index.md"
TAGS_FILE = "_vault-tags.md"
CACHE_FILE = "_vault-cache.json"
MANAGED_FILES = {INDEX_FILE, TAGS_FILE, CACHE_FILE}
UNINDEXED_DIRS = ("wiki/raw/", "wiki/Review/")
OVERRIDES_FILE = ".notes-index.toml"

# Large batches break local models' JSON.
TAG_BATCH_SIZE = 25
TAG_SAMPLE_SIZE = 6
CONTENT_LIMIT = 3000
SAVE_EVERY = 25

FILE_SUMMARY_PROMPT = """
You are a vault indexer. Your job is to write a single-sentence summary of a markdown note.

Rules:
- Output ONLY the summary sentence — no preamble, no quotes, no punctuation wrapping
- Maximum 25 words
- Be specific: mention the subject, not just the note type
- Good: "A recipe for chicken tikka masala with marinade and spiced tomato sauce."
- Bad: "This is a note about a recipe."

Special case — index files:
Files whose name starts with "index-" are category navigator files that link to other notes,
not content notes themselves. Summarise them by their role and the category they cover.
- Good: "Category index linking to all recipe notes in the vault."
- Good: "Navigation index for home lab notes, linking to tools, projects, and references."
- Bad: "A file containing a list of links."
"""

TAG_DESCRIPTION_PROMPT = """
You are a vault indexer. For each tag in the list below, write a one-sentence description
(max 20 words) of what notes with that tag cover.

Input format: a list of lines like:
  #tagname (N files): file1.md, file2.md, ...

Output a JSON object mapping each tag name (without #) to its description string.
Example output:
{
  "recipe": "Cooking recipes across various cuisines and techniques.",
  "book-notes": "Summaries and personal takeaways from non-fiction books."
}

Output ONLY the JSON object — no other text.
"""


def content_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_indexable(rel: str) -> bool:
    parts = PurePosixPath(rel).parts
    return (
        PurePosixPath(rel).name not in MANAGED_FILES
        and not rel.startswith(UNINDEXED_DIRS)
        and not any(p.startswith(".") for p in parts)
    )


def indexable_paths(root: Path) -> list[str]:
    rels = (p.relative_to(root).as_posix() for p in root.rglob("*.md") if p.is_file())
    return sorted(r for r in rels if is_indexable(r))


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
_FM_TAGS_INLINE_RE = re.compile(r"^tags:\s*\[([^\]]+)\]", re.MULTILINE | re.IGNORECASE)
_FM_TAGS_BLOCK_RE = re.compile(r"^tags:\s*\n((?:[ \t]+-[ \t]+\S+\n?)+)", re.MULTILINE | re.IGNORECASE)
_FM_TAG_ITEM_RE = re.compile(r"[ \t]+-[ \t]+(\S+)")
_INLINE_TAG_RE = re.compile(r"(?<!\S)#([A-Za-z][A-Za-z0-9_/-]*)")


def extract_tags(content: str) -> list[str]:
    tags: list[str] = []
    fm_match = _FRONTMATTER_RE.match(content)
    if fm_match:
        fm = fm_match.group(1)
        inline = _FM_TAGS_INLINE_RE.search(fm)
        if inline:
            tags.extend(t for t in (r.strip().strip("\"'") for r in inline.group(1).split(",")) if t)
        else:
            block = _FM_TAGS_BLOCK_RE.search(fm)
            if block:
                tags.extend(_FM_TAG_ITEM_RE.findall(block.group(1)))
    body = content[fm_match.end():] if fm_match else content
    tags.extend(_INLINE_TAG_RE.findall(body))
    return list(dict.fromkeys(tags))


def count_tags(root: Path, paths: list[str]) -> dict[str, list[str]]:
    tag_map: dict[str, list[str]] = {}
    for rel in paths:
        try:
            content = (root / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for tag in extract_tags(content):
            tag_map.setdefault(tag, []).append(rel)
    return tag_map


def load_cache(root: Path) -> dict:
    try:
        return json.loads((root / CACHE_FILE).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_cache(root: Path, summaries: dict, tag_cache: dict) -> None:
    tmp = root / f"{CACHE_FILE}.tmp"
    tmp.write_text(json.dumps(
        {"version": 1, "file_summaries": summaries, "tag_descriptions": tag_cache}, indent=2
    ), encoding="utf-8")
    os.replace(tmp, root / CACHE_FILE)


def stale_files(root: Path, paths: list[str], cache: dict) -> list[str]:
    cached = cache.get("file_summaries", {})
    stale = []
    for rel in paths:
        try:
            fresh = cached.get(rel, {}).get("sha256") == content_hash(root / rel)
        except OSError:
            fresh = False
        if not fresh:
            stale.append(rel)
    return stale


def stale_tags(tag_map: dict[str, list[str]], cache: dict) -> dict[str, list[str]]:
    cached = cache.get("tag_descriptions", {})
    return {
        tag: files for tag, files in tag_map.items()
        if cached.get(tag, {}).get("count_at_index") != len(files)
    }


def load_overrides(root: Path) -> dict[str, str]:
    path = root / OVERRIDES_FILE
    if not path.exists():
        return {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError) as e:
        print(f"warning: ignoring unreadable {path}: {e}", file=sys.stderr)
        return {}
    table = data.get("tag-descriptions", {})
    return {k: v for k, v in table.items() if isinstance(v, str)}


class AuthError(Exception):
    pass


def chat(system: str, user: str, *, base_url: str, model: str, api_key: str) -> str:
    body = json.dumps({
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system.strip()},
            {"role": "user", "content": user},
        ],
    }).encode()
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "x-litellm-end-user-id": END_USER,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.load(resp)["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise AuthError(f"endpoint rejected the key (HTTP {e.code})") from e
        raise


def summarize(rel: str, content: str, llm) -> str:
    out = llm(FILE_SUMMARY_PROMPT, f"File: {rel}\n\n{content[:CONTENT_LIMIT]}")
    text = out.strip().rstrip(".")
    if not text:
        raise ValueError("empty reply")
    return text + "."


def sample_files(files: list[str], k: int = TAG_SAMPLE_SIZE) -> list[str]:
    """Even spacing avoids alphabetical bias."""
    if len(files) <= k:
        return list(files)
    step = len(files) / k
    return [files[int(i * step)] for i in range(k)]


def tag_context(tag: str, files: list[str], summaries: dict[str, dict]) -> str:
    lines = [f"#{tag} ({len(files)} files):"]
    for rel in sample_files(files):
        s = (summaries.get(rel) or {}).get("summary", "")
        lines.append(f"  - {rel}" + (f" — {s}" if s else ""))
    return "\n".join(lines)


def parse_json_response(raw: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE).strip()
    return json.loads(text)


def describe_tags(
    pending: dict[str, list[str]], summaries: dict[str, dict], llm
) -> tuple[dict[str, str], int]:
    """Returns descriptions and failed-tag count."""
    results: dict[str, str] = {}
    failed = 0
    items = sorted(pending.items())
    batches = [items[i:i + TAG_BATCH_SIZE] for i in range(0, len(items), TAG_BATCH_SIZE)]
    for n, batch in enumerate(batches, 1):
        print(f"tags: batch {n}/{len(batches)}")
        block = "\n\n".join(tag_context(t, f, summaries) for t, f in batch)
        try:
            parsed = parse_json_response(
                llm(TAG_DESCRIPTION_PROMPT, f"Generate descriptions for these vault tags:\n\n{block}")
            )
            wanted = {t for t, _ in batch}
            for key, val in parsed.items():
                key = key.removeprefix("#")
                if key in wanted and isinstance(val, str):
                    results[key] = val
        except AuthError:
            raise
        except Exception as e:
            failed += len(batch)
            print(f"warning: tag batch {n}/{len(batches)} failed: {e}", file=sys.stderr)
    return results, failed


def _escape(text: str) -> str:
    return " ".join(text.split()).replace("|", "\\|")


def render_index(entries: list[tuple[str, str]], now: str) -> str:
    lines = ["# Vault Index", MARKER, f"_Last updated: {now}_", "",
             "| File | Summary |", "|------|---------|"]
    lines += [f"| {path} | {_escape(summary)} |" for path, summary in sorted(entries)]
    return "\n".join(lines + [""])


def render_tags(entries: list[tuple[str, int, str]], now: str) -> str:
    lines = ["# Vault Tags", MARKER, f"_Last updated: {now}_", "",
             "| Tag | Count | Description |", "|-----|-------|-------------|"]
    for tag, count, desc in sorted(entries, key=lambda e: (-e[1], e[0])):
        lines.append(f"| #{tag} | {count} | {_escape(desc)} |")
    return "\n".join(lines + [""])


def run(root: Path, llm, *, force=False, run_files=True, run_tags=True, concurrency=8) -> int:
    """Returns the failure count."""
    cache = load_cache(root)
    if force:
        # Keep the section this run won't regenerate.
        if run_files:
            cache.pop("file_summaries", None)
        if run_tags:
            cache.pop("tag_descriptions", None)
    summaries: dict = cache.get("file_summaries", {})
    tag_cache: dict = cache.get("tag_descriptions", {})
    paths = indexable_paths(root)
    failed = 0

    if run_files:
        todo = stale_files(root, paths, {"file_summaries": summaries})

        def one(rel: str) -> tuple[str, dict]:
            try:
                digest = content_hash(root / rel)
                content = (root / rel).read_text(encoding="utf-8")
                return rel, {"sha256": digest, "summary": summarize(rel, content, llm)}
            except AuthError:
                raise
            except Exception as e:
                print(f"warning: {rel}: {e}", file=sys.stderr)
                return rel, {"sha256": "", "summary": UNAVAILABLE}

        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
            futures = [pool.submit(one, rel) for rel in todo]
            try:
                for done, fut in enumerate(as_completed(futures), 1):
                    rel, entry = fut.result()
                    summaries[rel] = entry
                    failed += entry["sha256"] == ""
                    print(f"[{done}/{len(todo)}] {rel}")
                    if done % SAVE_EVERY == 0:
                        save_cache(root, summaries, tag_cache)
            except AuthError:
                pool.shutdown(wait=False, cancel_futures=True)
                raise
            except BaseException:
                pool.shutdown(wait=False, cancel_futures=True)
                save_cache(root, summaries, tag_cache)
                raise

    tag_map: dict[str, list[str]] = {}
    overrides = load_overrides(root)
    if run_tags:
        tag_map = count_tags(root, paths)
        pending = {t: f for t, f in stale_tags(tag_map, {"tag_descriptions": tag_cache}).items()
                   if t not in overrides}
        if pending:
            described, tag_failures = describe_tags(pending, summaries, llm)
            failed += tag_failures
            for tag, desc in described.items():
                tag_cache[tag] = {"count_at_index": len(tag_map.get(tag, [])), "description": desc}

    summaries = {p: summaries[p] for p in paths if p in summaries}
    save_cache(root, summaries, tag_cache)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    if run_files:
        entries = [(p, summaries[p]["summary"]) for p in paths if p in summaries]
        (root / INDEX_FILE).write_text(render_index(entries, now), encoding="utf-8")
        print(f"{len(entries)} files -> {INDEX_FILE}")
    if run_tags:
        tag_entries = [
            (t, len(f), overrides.get(t, tag_cache.get(t, {}).get("description", "")))
            for t, f in tag_map.items()
        ]
        (root / TAGS_FILE).write_text(render_tags(tag_entries, now), encoding="utf-8")
        print(f"{len(tag_entries)} tags -> {TAGS_FILE}")
    if failed:
        print(f"{failed} summaries or tags failed; rerun to retry", file=sys.stderr)
    return failed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Regenerate a vault's index, tags and cache files.")
    ap.add_argument("vault", nargs="?", default="~/Git/notes", help="vault directory (default: %(default)s)")
    ap.add_argument("--force", action="store_true", help="ignore the cache")
    only = ap.add_mutually_exclusive_group()
    only.add_argument("--only-files", action="store_true", help="regenerate _vault-index.md only")
    only.add_argument("--only-tags", action="store_true", help="regenerate _vault-tags.md only")
    ap.add_argument("--concurrency", type=int, default=8, help="summaries in flight (default: %(default)s)")
    args = ap.parse_args(argv)

    api_key = os.environ.get("NOTES_INDEX_API_KEY") or os.environ.get("LITELLM_API_KEY")
    if not api_key:
        print("error: set NOTES_INDEX_API_KEY or LITELLM_API_KEY", file=sys.stderr)
        return 2

    base_url = os.environ.get("NOTES_INDEX_BASE_URL", DEFAULT_BASE_URL)
    model = os.environ.get("NOTES_INDEX_MODEL", DEFAULT_MODEL)

    def llm(system: str, user: str) -> str:
        return chat(system, user, base_url=base_url, model=model, api_key=api_key)

    root = Path(args.vault).expanduser()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2
    try:
        failed = run(root, llm, force=args.force, run_files=not args.only_tags,
                     run_tags=not args.only_files, concurrency=args.concurrency)
    except AuthError as e:
        print(f"error: {e}; nothing written", file=sys.stderr)
        return 2
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
