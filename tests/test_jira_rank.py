"""jira-rank.py validates keys, ranks after the first key, and verifies."""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from _loader import load

jr = load("jira-rank.py")

_NO_TOOLBOX = tempfile.mkdtemp()  # never read the real work.env
ENV = {"JIRA_EMAIL": "me@example.com", "JIRA_API_TOKEN": "t", "TOOLBOX_HOME": _NO_TOOLBOX}


def _response(status: int, body: dict | None) -> mock.MagicMock:
    """Fake a urlopen context manager."""
    resp = mock.MagicMock()
    resp.__enter__.return_value = resp
    resp.status = status
    resp.read.return_value = json.dumps(body).encode() if body is not None else b""
    return resp


def _search(*keys: str) -> mock.MagicMock:
    """Fake a search: keys given in rank order, returned shuffled."""
    issues = [{"key": k, "fields": {jr.RANK_FIELD: f"0|a{n:04d}:"}} for n, k in enumerate(keys)]
    return _response(200, {"issues": issues[::-1]})


def _methods(urlopen: mock.MagicMock) -> list[str]:
    """HTTP methods sent, in order."""
    return [c.args[0].get_method() for c in urlopen.call_args_list]


def _run(argv: list[str], responses: list) -> tuple[int, mock.MagicMock, str]:
    """Run main with canned responses; return code, mock, stderr."""
    err = io.StringIO()
    with mock.patch.object(jr.urllib.request, "urlopen", side_effect=responses) as urlopen, \
            redirect_stdout(io.StringIO()), redirect_stderr(err):
        code = jr.main(argv)
    return code, urlopen, err.getvalue()


class TestToKeys(unittest.TestCase):
    def test_numbers_and_lowercase_become_upper_keys(self):
        self.assertEqual(jr.to_keys(["5326", "mntor-5324"], "mntor"), ["MNTOR-5326", "MNTOR-5324"])

    def test_duplicates_are_rejected(self):
        with self.assertRaises(ValueError):
            jr.to_keys(["5326", "MNTOR-5326"], "MNTOR")

    def test_malformed_keys_are_rejected(self):
        for bad in ("abc", "5326)", "MNTOR-"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                jr.to_keys([bad, "5324"], "MNTOR")


class FreshSecrets(unittest.TestCase):
    def setUp(self) -> None:
        """Drop cached secrets between tests."""
        jr.secret.cache_clear()


class TestSecret(FreshSecrets):
    def _toolbox(self, text: str) -> str:
        """Make a temp toolbox holding work.env."""
        root = tempfile.mkdtemp()
        d = Path(root, "nixos", "secrets")
        d.mkdir(parents=True)
        (d / "work.env").write_text(text)
        return root

    def test_env_wins_and_skips_op(self):
        with mock.patch.dict(os.environ, {"JIRA_EMAIL": "env@example.com"}), \
                mock.patch.object(jr.subprocess, "run") as run:
            self.assertEqual(jr.secret("JIRA_EMAIL"), "env@example.com")
        run.assert_not_called()

    def test_ref_from_work_env_is_resolved_by_op(self):
        root = self._toolbox("OTHER=x\nJIRA_API_TOKEN_REF=V/Item/credential\n")
        done = mock.Mock(stdout="tok\n")
        with mock.patch.dict(os.environ, {"JIRA_API_TOKEN": "", "JIRA_API_TOKEN_REF": "", "TOOLBOX_HOME": root}), \
                mock.patch.object(jr.subprocess, "run", return_value=done) as run:
            self.assertEqual(jr.secret("JIRA_API_TOKEN"), "tok")
        self.assertEqual(run.call_args.args[0], ["op", "read", "op://V/Item/credential"])

    def test_op_failure_gives_none(self):
        with mock.patch.dict(os.environ, {"JIRA_API_TOKEN": "", "JIRA_API_TOKEN_REF": "op://V/I/c"}), \
                mock.patch.object(jr.subprocess, "run", side_effect=FileNotFoundError("op")), \
                redirect_stderr(io.StringIO()):
            self.assertIsNone(jr.secret("JIRA_API_TOKEN"))

    def test_no_value_and_no_ref_gives_none(self):
        with mock.patch.dict(os.environ, {"JIRA_API_TOKEN": "", "JIRA_API_TOKEN_REF": "", "TOOLBOX_HOME": _NO_TOOLBOX}):
            self.assertIsNone(jr.secret("JIRA_API_TOKEN"))


@mock.patch.dict(os.environ, ENV)
class TestRequests(FreshSecrets):
    def test_rank_puts_the_rest_after_the_first(self):
        with mock.patch.object(jr.urllib.request, "urlopen", return_value=_response(204, None)) as urlopen:
            jr.rank(["MNTOR-1", "MNTOR-2", "MNTOR-3"])
        req = urlopen.call_args.args[0]
        self.assertEqual(req.get_method(), "PUT")
        self.assertTrue(req.full_url.startswith(jr.DEFAULT_BASE_URL))
        self.assertEqual(json.loads(req.data), {"issues": ["MNTOR-2", "MNTOR-3"], "rankAfterIssue": "MNTOR-1"})

    def test_base_url_can_be_overridden(self):
        with mock.patch.dict(os.environ, {"JIRA_BASE_URL": "https://x.example"}), \
                mock.patch.object(jr.urllib.request, "urlopen", return_value=_response(204, None)) as urlopen:
            jr.rank(["MNTOR-1", "MNTOR-2"])
        self.assertEqual(urlopen.call_args.args[0].full_url, "https://x.example" + jr.RANK_PATH)

    def test_partial_failure_names_the_failed_ticket(self):
        body = {"entries": [{"issueKey": "MNTOR-2", "status": 200}, {"issueKey": "MNTOR-3", "status": 403}]}
        with mock.patch.object(jr.urllib.request, "urlopen", return_value=_response(207, body)):
            with self.assertRaisesRegex(jr.JiraError, "MNTOR-3") as ctx:
                jr.rank(["MNTOR-1", "MNTOR-2", "MNTOR-3"])
        self.assertNotIn("MNTOR-2 ", str(ctx.exception))

    def test_207_with_all_successes_does_not_raise(self):
        body = {"entries": [{"issueKey": "MNTOR-2", "status": 200}]}
        with mock.patch.object(jr.urllib.request, "urlopen", return_value=_response(207, body)):
            jr.rank(["MNTOR-1", "MNTOR-2"])

    def test_search_asks_for_every_key(self):
        keys = [f"MNTOR-{n}" for n in range(1, 52)]
        with mock.patch.object(jr.urllib.request, "urlopen", return_value=_search(*keys)) as urlopen:
            self.assertEqual(jr.current_order(keys), keys)
        sent = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual(sent["maxResults"], 51)
        self.assertEqual(sent["fields"], [jr.RANK_FIELD])

    def test_order_comes_from_rank_values_not_result_order(self):
        body = {"issues": [{"key": "MNTOR-1", "fields": {jr.RANK_FIELD: "2|hy0ykq:"}},
                           {"key": "MNTOR-2", "fields": {jr.RANK_FIELD: "2|hy0yko:"}}]}
        with mock.patch.object(jr.urllib.request, "urlopen", return_value=_response(200, body)):
            self.assertEqual(jr.current_order(["MNTOR-1", "MNTOR-2"]), ["MNTOR-2", "MNTOR-1"])

    def test_http_error_carries_method_path_and_hint(self):
        err = urllib.error.HTTPError("u", 401, "no", {}, io.BytesIO(b"nope"))
        with mock.patch.object(jr.urllib.request, "urlopen", side_effect=err):
            with self.assertRaisesRegex(jr.JiraError, r"PUT /rest/agile/1.0/issue/rank 401 \(check"):
                jr.rank(["MNTOR-1", "MNTOR-2"])


@mock.patch.dict(os.environ, ENV)
class TestMain(FreshSecrets):
    def test_success_searches_ranks_then_verifies(self):
        code, urlopen, _ = _run(["2", "1"], [_search("MNTOR-1", "MNTOR-2"), _response(204, None),
                                             _search("MNTOR-2", "MNTOR-1")])
        self.assertEqual(code, 0)
        self.assertEqual(_methods(urlopen), ["POST", "PUT", "POST"])

    def test_dry_run_sends_no_put(self):
        code, urlopen, _ = _run(["--dry-run", "2", "1"], [_search("MNTOR-1", "MNTOR-2")])
        self.assertEqual(code, 0)
        self.assertEqual(_methods(urlopen), ["POST"])

    def test_dry_run_still_reports_missing_tickets(self):
        code, _, err = _run(["--dry-run", "2", "1"], [_search("MNTOR-1")])
        self.assertEqual(code, 1)
        self.assertIn("not found: MNTOR-2", err)

    def test_already_in_order_skips_the_put(self):
        code, urlopen, _ = _run(["1", "2"], [_search("MNTOR-1", "MNTOR-2")])
        self.assertEqual(code, 0)
        self.assertEqual(_methods(urlopen), ["POST"])

    def test_wrong_order_after_rank_fails_loudly(self):
        code, _, err = _run(["2", "1"], [_search("MNTOR-1", "MNTOR-2"), _response(204, None),
                                         _search("MNTOR-1", "MNTOR-2")])
        self.assertEqual(code, 1)
        self.assertIn("order mismatch", err)

    def test_network_failure_exits_cleanly(self):
        code, _, err = _run(["2", "1"], [urllib.error.URLError("offline")])
        self.assertEqual(code, 1)
        self.assertIn("unreachable", err)

    def test_bad_input_exits_2(self):
        for argv in (["1"], [str(n) for n in range(52)], ["1", "1"], ["abc", "1"]):
            with self.subTest(argv=argv), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ctx:
                jr.main(argv)
            self.assertEqual(ctx.exception.code, 2)

    def test_missing_env_exits_2(self):
        with mock.patch.dict(os.environ, {"JIRA_API_TOKEN": "", "JIRA_API_TOKEN_REF": ""}), redirect_stderr(io.StringIO()), \
                self.assertRaises(SystemExit) as ctx:
            jr.main(["1", "2"])
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
