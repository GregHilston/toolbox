"""notes-index: indexable files, tags, content-keyed cache, failures, overrides."""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load

ni = load("notes-index.py")


def fake_llm(system: str, user: str) -> str:
    if system is ni.TAG_DESCRIPTION_PROMPT:
        tags = [ln[1:].split(" ")[0] for ln in user.splitlines() if ln.startswith("#")]
        return json.dumps({t: f"About {t}." for t in tags})
    return "A short summary."


class Vault(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def write(self, rel: str, text: str = "hello") -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def run_index(self, llm=fake_llm, **kw) -> int:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return ni.run(self.root, llm, **kw)

    def cache(self) -> dict:
        return json.loads((self.root / "_vault-cache.json").read_text())


class IsIndexable(unittest.TestCase):
    def test_rules(self):
        for rel, ok in {
            "a.md": True,
            "recipes/b.md": True,
            "_vault-index.md": False,
            "sub/_vault-tags.md": False,
            "wiki/raw/x.md": False,
            "wiki/Review/x.md": False,
            "wiki/page.md": True,
            ".obsidian/x.md": False,
            "dir/.hidden/x.md": False,
        }.items():
            self.assertEqual(ni.is_indexable(rel), ok, rel)

    def test_only_markdown_listed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.md").write_text("x")
            (root / "b.txt").write_text("x")
            (root / "_vault-cache.json").write_text("{}")
            self.assertEqual(ni.indexable_paths(root), ["a.md"])


class ExtractTags(unittest.TestCase):
    def test_sources_and_dedupe(self):
        self.assertEqual(ni.extract_tags("---\ntags: [a, \"b\"]\n---\nbody #c #a"), ["a", "b", "c"])

    def test_block_list(self):
        self.assertEqual(ni.extract_tags("---\ntags:\n  - x\n  - y\n---\n"), ["x", "y"])

    def test_ignores_url_fragments_and_digits(self):
        self.assertEqual(ni.extract_tags("see http://e.com/#frag and #1 and a #real"), ["real"])


class Staleness(Vault):
    def test_mtime_alone_is_not_stale(self):
        p = self.write("a.md", "same")
        self.run_index()
        os.utime(p, (1, 1))
        calls = []
        self.run_index(lambda s, u: calls.append(u) or fake_llm(s, u))
        self.assertEqual(calls, [])

    def test_content_change_is_stale(self):
        p = self.write("a.md", "one")
        self.run_index()
        p.write_text("two")
        self.assertEqual(ni.stale_files(self.root, ["a.md"], self.cache()), ["a.md"])

    def test_entry_without_sha_is_stale(self):
        self.write("a.md")
        cache = {"file_summaries": {"a.md": {"mtime": 1.0, "summary": "old"}}}
        self.assertEqual(ni.stale_files(self.root, ["a.md"], cache), ["a.md"])

    def test_tag_stale_on_count_change(self):
        tag_map = {"t": ["a.md", "b.md"]}
        cache = {"tag_descriptions": {"t": {"count_at_index": 1, "description": "d"}}}
        self.assertEqual(ni.stale_tags(tag_map, cache), tag_map)
        cache["tag_descriptions"]["t"]["count_at_index"] = 2
        self.assertEqual(ni.stale_tags(tag_map, cache), {})


class Failures(Vault):
    def test_failure_retried_and_exit_code(self):
        self.write("a.md", "#t")

        def boom(s, u):
            raise RuntimeError("down")

        self.assertEqual(self.run_index(boom), 2)  # one summary, one tag
        entry = self.cache()["file_summaries"]["a.md"]
        self.assertEqual(entry, {"sha256": "", "summary": "(summary unavailable)"})
        self.assertIn("(summary unavailable)", (self.root / "_vault-index.md").read_text())

        self.assertEqual(self.run_index(), 0)
        entry = self.cache()["file_summaries"]["a.md"]
        self.assertNotEqual(entry["sha256"], "")
        self.assertEqual(entry["summary"], "A short summary.")

    def test_main_exits_1_on_failure(self):
        self.write("a.md")
        env = {"NOTES_INDEX_API_KEY": "k"}
        with mock.patch.dict(os.environ, env), mock.patch.object(ni, "chat", side_effect=OSError("x")):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(ni.main([str(self.root)]), 1)


class Overrides(Vault):
    def test_loaded_from_vault_toml_and_skip_llm(self):
        self.write("a.md", "#fixed #free")
        self.write(".notes-index.toml", '[tag-descriptions]\nfixed = "Hand written."\n')
        self.assertEqual(ni.load_overrides(self.root), {"fixed": "Hand written."})
        seen = []

        def llm(s, u):
            if s is ni.TAG_DESCRIPTION_PROMPT:
                seen.append(u)
            return fake_llm(s, u)

        self.run_index(llm)
        self.assertTrue(seen)
        self.assertFalse(any("#fixed" in u for u in seen))
        tags = (self.root / "_vault-tags.md").read_text()
        self.assertIn("| #fixed | 1 | Hand written. |", tags)
        self.assertIn("| #free | 1 | About free. |", tags)

    def test_missing_file_means_none(self):
        self.assertEqual(ni.load_overrides(self.root), {})


class Credentials(unittest.TestCase):
    def test_missing_key_exits_2_without_request(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(ni, "chat") as chat:
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(ni.main(["/nonexistent"]), 2)
        chat.assert_not_called()
        self.assertIn("NOTES_INDEX_API_KEY", err.getvalue())
        self.assertIn("LITELLM_API_KEY", err.getvalue())

    def test_litellm_key_fallback(self):
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.dict(os.environ, {"LITELLM_API_KEY": "k"}, clear=True), \
                mock.patch.object(ni, "chat", return_value="Ok.") as chat:
            Path(d, "a.md").write_text("x")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ni.main([d, "--only-files"]), 0)
        self.assertEqual(chat.call_args.kwargs["api_key"], "k")
        self.assertEqual(chat.call_args.kwargs["model"], "local-small")


class Format(Vault):
    def test_headers_and_rows(self):
        self.write("a.md", "---\ntags: [x]\n---\n")
        self.write("b.md", "#x #y")
        self.run_index(lambda s, u: "Pipes | here" if s is ni.FILE_SUMMARY_PROMPT else fake_llm(s, u))
        index = (self.root / "_vault-index.md").read_text().splitlines()
        self.assertEqual(index[0], "# Vault Index")
        self.assertEqual(index[1], "<!-- managed by notes-index: do not edit manually — regenerate with `notes-index.py` -->")
        self.assertTrue(index[2].startswith("_Last updated: "))
        self.assertEqual(index[4:6], ["| File | Summary |", "|------|---------|"])
        self.assertEqual(index[6], "| a.md | Pipes \\| here. |")
        tags = (self.root / "_vault-tags.md").read_text().splitlines()
        self.assertEqual(tags[0], "# Vault Tags")
        self.assertEqual(tags[1], index[1])
        self.assertEqual(tags[4:6], ["| Tag | Count | Description |", "|-----|-------|-------------|"])
        self.assertEqual(tags[6], "| #x | 2 | About x. |")
        self.assertEqual(tags[7], "| #y | 1 | About y. |")
        self.assertEqual(self.cache()["version"], 1)

    def test_user_message_truncates_to_3000(self):
        seen = []
        ni.summarize("n.md", "z" * 5000, lambda s, u: seen.append(u) or "ok")
        self.assertEqual(seen[0], "File: n.md\n\n" + "z" * 3000)

    def test_only_tags_skips_summaries(self):
        self.write("a.md", "#t")
        self.run_index(run_files=False)
        self.assertFalse((self.root / "_vault-index.md").exists())
        self.assertTrue((self.root / "_vault-tags.md").exists())


class Hardening(Vault):
    def test_directory_and_broken_symlink_do_not_crash(self):
        self.write("ok.md")
        (self.root / "x.md").mkdir()
        (self.root / "dead.md").symlink_to(self.root / "missing")
        self.assertEqual(ni.indexable_paths(self.root), ["ok.md"])
        self.assertEqual(self.run_index(), 0)

    def test_unreadable_file_is_stale_and_fails(self):
        p = self.write("a.md")
        p.chmod(0)
        self.addCleanup(p.chmod, 0o644)
        if os.access(p, os.R_OK):
            self.skipTest("permissions not enforced")
        self.assertEqual(ni.stale_files(self.root, ["a.md"], {}), ["a.md"])
        self.assertEqual(self.run_index(), 1)

    def test_empty_reply_is_a_failure(self):
        self.write("a.md")
        self.assertEqual(self.run_index(lambda s, u: "  . "), 1)
        self.assertEqual(self.cache()["file_summaries"]["a.md"]["sha256"], "")

    def test_force_only_tags_preserves_summaries(self):
        self.write("a.md", "#t")
        self.run_index()
        calls = []
        self.run_index(lambda s, u: calls.append(s) or fake_llm(s, u), force=True, run_files=False)
        self.assertNotIn(ni.FILE_SUMMARY_PROMPT, calls)
        self.assertEqual(self.cache()["file_summaries"]["a.md"]["summary"], "A short summary.")

    def test_force_only_files_preserves_tag_descriptions(self):
        self.write("a.md", "#t")
        self.run_index()
        calls = []
        self.run_index(lambda s, u: calls.append(s) or fake_llm(s, u), force=True, run_tags=False)
        self.assertNotIn(ni.TAG_DESCRIPTION_PROMPT, calls)
        self.assertIn("t", self.cache()["tag_descriptions"])

    def test_failed_tag_batch_gives_failures(self):
        self.write("a.md", "#t")

        def llm(s, u):
            if s is ni.TAG_DESCRIPTION_PROMPT:
                return "not json"
            return fake_llm(s, u)

        self.assertEqual(self.run_index(llm), 1)
        self.assertEqual(self.run_index(), 0)

    def test_deleted_note_is_pruned(self):
        self.write("a.md")
        gone = self.write("b.md")
        self.run_index()
        gone.unlink()
        self.run_index()
        self.assertEqual(list(self.cache()["file_summaries"]), ["a.md"])

    def test_multiline_summary_stays_in_one_cell(self):
        self.write("a.md")
        self.run_index(lambda s, u: "Line one\n\nline two")
        self.assertIn("| a.md | Line one line two. |", (self.root / "_vault-index.md").read_text())

    def test_auth_error_aborts_with_exit_2_and_writes_nothing(self):
        import urllib.error

        for n in range(5):
            self.write(f"n{n}.md")
        err = urllib.error.HTTPError("u", 401, "no", {}, None)
        with mock.patch.dict(os.environ, {"NOTES_INDEX_API_KEY": "k"}), \
                mock.patch("urllib.request.urlopen", side_effect=err):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(ni.main([str(self.root), "--concurrency", "1"]), 2)
        self.assertEqual(sorted(p.name for p in self.root.iterdir() if p.suffix != ".md"), [])

    def test_other_http_errors_are_per_file(self):
        import urllib.error

        self.write("a.md")
        err = urllib.error.HTTPError("u", 500, "boom", {}, None)
        with mock.patch.dict(os.environ, {"NOTES_INDEX_API_KEY": "k"}), \
                mock.patch("urllib.request.urlopen", side_effect=err):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(ni.main([str(self.root)]), 1)


class TagParsing(unittest.TestCase):
    def test_code_fences(self):
        self.assertEqual(ni.parse_json_response('```json\n{"a": "b"}\n```'), {"a": "b"})
        self.assertEqual(ni.parse_json_response('```\n{"a": "b"}\n```'), {"a": "b"})

    def test_invented_keys_dropped_and_hash_stripped(self):
        reply = json.dumps({"real": "R.", "#other": "O.", "invented": "I."})
        with contextlib.redirect_stdout(io.StringIO()):
            results, failed = ni.describe_tags({"real": ["a.md"], "other": ["b.md"]}, {}, lambda s, u: reply)
        self.assertEqual(results, {"real": "R.", "other": "O."})
        self.assertEqual(failed, 0)


if __name__ == "__main__":
    unittest.main()
