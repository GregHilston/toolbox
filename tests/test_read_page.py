"""read-page.py tries defuddle, then Jina, then gives up with a reason.

Fixtures are trimmed real responses (2026-09-27); upstream drift shows up
in test_keyless_tools_live.py instead.
"""

from __future__ import annotations

import subprocess
import unittest
from unittest import mock

from _loader import load

page = load("read-page.py")


LONG = "word " * 200


class TestReadPage(unittest.TestCase):
    def _run(self, stdout: str, code: int = 0):
        return mock.patch.object(page.subprocess, "run", return_value=subprocess.CompletedProcess([], code, stdout, ""))

    def test_defuddle_first(self):
        with mock.patch.object(page, "defuddle_cmd", return_value=["defuddle"]), \
             self._run(f'{{"title": "T", "contentMarkdown": "{LONG}"}}'), \
             mock.patch.object(page, "jina") as jina:
            self.assertEqual(page.read("https://example.com")[::2], ("T", "defuddle"))
        jina.assert_not_called()

    def test_a_thin_defuddle_result_falls_back_to_jina(self):
        with mock.patch.object(page, "defuddle_cmd", return_value=["defuddle"]), \
             self._run('{"title": "T", "contentMarkdown": "Enable cookies"}'), \
             mock.patch.object(page, "jina", return_value=("J", LONG)):
            self.assertEqual(page.read("https://example.com")[::2], ("J", "jina"))

    def test_a_failed_defuddle_falls_back_to_jina(self):
        with mock.patch.object(page, "defuddle_cmd", return_value=["defuddle"]), self._run("", 1), \
             mock.patch.object(page, "jina", return_value=("J", LONG)):
            self.assertEqual(page.read("https://example.com")[2], "jina")

    def test_both_failing_is_an_error_not_a_loop(self):
        with mock.patch.object(page, "defuddle", return_value=None), \
             mock.patch.object(page, "jina", return_value=None) as jina:
            with self.assertRaisesRegex(LookupError, "JavaScript"):
                page.read("https://bsky.app/x")
        jina.assert_called_once()

    def test_a_lab_url_never_goes_to_jina(self):
        for url in ("http://home-assistant:8123/api", "http://192.168.1.2/x", "https://nas.local/", "http://localhost:8000"):
            with self.subTest(url=url), mock.patch.object(page, "defuddle", return_value=None), \
                 mock.patch.object(page, "jina") as jina:
                with self.assertRaises(LookupError):
                    page.read(url)
                jina.assert_not_called()
        self.assertTrue(page.public("https://simonwillison.net/x"))

    def test_npx_runs_the_pinned_version_without_a_global_install(self):
        with mock.patch.object(page.shutil, "which", side_effect=lambda c: "/bin/npx" if c == "npx" else None):
            self.assertEqual(page.defuddle_cmd(), ["npx", "-y", f"defuddle@{page.DEFUDDLE_VERSION}"])

    def test_jina_header_is_split_from_the_body(self):
        resp = mock.MagicMock()
        resp.__enter__.return_value = resp
        resp.read.return_value = f"Title: A page\n\nURL Source: https://x\n\nMarkdown Content:\n{LONG}".encode()
        with mock.patch.object(page.urllib.request, "urlopen", return_value=resp):
            title, body = page.jina("https://example.com")
        self.assertEqual(title, "A page")
        self.assertTrue(body.startswith("word"))


if __name__ == "__main__":
    unittest.main()
