"""needs-greg: the ask parser, the config loader, and the commands it would run."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from _loader import load

ng = load("needs-greg/server.py")

BLOCK = "```ask\n{}\n```\n\nbody text"


class ParseTest(unittest.TestCase):
    def test_no_block_is_none(self) -> None:
        self.assertIsNone(ng.parse_ask("just a body"))
        self.assertIsNone(ng.parse_ask(None))

    def test_full_block_with_comments(self) -> None:
        a = ng.parse_ask(BLOCK.format(
            "ask: Pick the icon style for the five #45 cards.\n"
            "type: pick        # pick | text | done\n"
            "options: A = flat; B = pixel; C = none\n"
            "minutes: 2\n"
            "images: art/one.jpg, art/two.png"))
        self.assertEqual(a.ask, "Pick the icon style for the five #45 cards.")
        self.assertEqual(a.type, "pick")
        self.assertEqual([o["key"] for o in a.options], ["A", "B", "C"])
        self.assertEqual(a.options[1]["label"], "pixel")
        self.assertEqual(a.minutes, 2)
        self.assertEqual(a.images, ["art/one.jpg", "art/two.png"])

    def test_bad_type(self) -> None:
        with self.assertRaisesRegex(ng.AskError, "type"):
            ng.parse_ask(BLOCK.format("ask: x\ntype: vote"))

    def test_missing_ask(self) -> None:
        with self.assertRaisesRegex(ng.AskError, "ask"):
            ng.parse_ask(BLOCK.format("type: text"))

    def test_pick_without_options(self) -> None:
        with self.assertRaisesRegex(ng.AskError, "options"):
            ng.parse_ask(BLOCK.format("ask: x\ntype: pick"))

    def test_option_without_equals(self) -> None:
        with self.assertRaisesRegex(ng.AskError, "KEY"):
            ng.parse_ask(BLOCK.format("ask: x\ntype: pick\noptions: A; B"))

    def test_multiline_values(self) -> None:
        a = ng.parse_ask(BLOCK.format(
            "ask: Choose the style\n  that fits the cards.\n"
            "type: pick\n"
            "options:\n  - A = flat\n  - B = pixel\n"
            "images: a.jpg,\n  b.jpg"))
        self.assertEqual(a.ask, "Choose the style that fits the cards.")
        self.assertEqual([o["key"] for o in a.options], ["A", "B"])
        self.assertEqual(a.images, ["a.jpg", "b.jpg"])

    def test_crlf_body(self) -> None:
        body = "```ask\r\nask: Hi\r\ntype: done\r\n```\r\n\r\ntext"
        self.assertEqual(ng.parse_ask(body).ask, "Hi")

    def test_block_must_open_the_body(self) -> None:
        self.assertEqual(ng.parse_ask("\n\n" + BLOCK.format("ask: x\ntype: done")).type, "done")
        self.assertIsNone(ng.parse_ask("intro\n\n" + BLOCK.format("ask: x\ntype: done")))

    def test_bad_minutes(self) -> None:
        with self.assertRaisesRegex(ng.AskError, "minutes"):
            ng.parse_ask(BLOCK.format("ask: x\ntype: done\nminutes: soon"))


CONFIG = """
owner = "owner"
login = "user@example.com"
session_host = "local"
[repos]
repo-a = "/x/repo-a"
"""


def write_config(text: str) -> Path:
    d = tempfile.mkdtemp()
    p = Path(d) / "config.toml"
    p.write_text(text)
    return p


class ConfigTest(unittest.TestCase):
    def test_defaults(self) -> None:
        c = ng.load_config(write_config(CONFIG))
        self.assertEqual((c.port, c.label, c.herdr), (8765, "needs-greg", "herdr"))
        self.assertEqual(c.repos, {"repo-a": "/x/repo-a"})

    def test_missing_key(self) -> None:
        with self.assertRaisesRegex(ng.ConfigError, "login"):
            ng.load_config(write_config('owner = "o"\nsession_host = "h"\n[repos]\na = "/a"'))

    def test_no_repos(self) -> None:
        with self.assertRaisesRegex(ng.ConfigError, "repos"):
            ng.load_config(write_config('owner = "o"\nlogin = "l"\nsession_host = "h"'))

    def test_missing_file(self) -> None:
        with self.assertRaisesRegex(ng.ConfigError, "no config"):
            ng.load_config(Path("/nonexistent/config.toml"))

    def test_local_versus_ssh(self) -> None:
        c = ng.load_config(write_config(CONFIG))
        self.assertTrue(ng.session_is_local(c))
        c.session_host = "host-a"
        self.assertFalse(ng.session_is_local(c))

    def test_session_host_cannot_be_an_ssh_option(self) -> None:
        with self.assertRaisesRegex(ng.ConfigError, "must not start"):
            ng.load_config(write_config(CONFIG.replace('"local"', '"-oProxyCommand=x"')))
        run, rec = runner(host="host-b")
        run.herdr(["workspace", "create"], write=True)
        self.assertIn("ssh -o BatchMode=yes -o ConnectTimeout=8 -- host-b ", rec.lines[0])

    def test_binary_paths(self) -> None:
        c = ng.load_config(write_config('gh = "/opt/gh"\nherdr = "/opt/herdr"\n' + CONFIG))
        self.assertEqual((c.gh, c.herdr), ("/opt/gh", "/opt/herdr"))


class Recorder:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def __call__(self, msg: str) -> None:
        self.lines.append(msg)


def runner(host: str = "local", dry: bool = True) -> tuple:
    cfg = ng.load_config(write_config(CONFIG))
    cfg.session_host = host
    rec = Recorder()
    return ng.Runner(cfg, dry_run=dry, log=rec), rec


class CommandTest(unittest.TestCase):
    def test_answer_pick_logs_comment_then_label_removal(self) -> None:
        run, rec = runner()
        ng.answer(run, "repo-a", 7, "pick", "B", "go pixel")
        self.assertEqual(len(rec.lines), 2)
        self.assertIn("issue comment 7 --repo owner/repo-a --body", rec.lines[0])
        self.assertIn("Decision: B", rec.lines[0])
        self.assertIn("issue edit 7 --repo owner/repo-a --remove-label needs-greg", rec.lines[1])

    def test_answer_text_and_done(self) -> None:
        run, rec = runner()
        self.assertEqual(ng.answer(run, "repo-a", 1, "text", "yes")["comment"], "Answer: yes")
        self.assertEqual(ng.answer(run, "repo-a", 1, "done")["comment"], "Done.")
        self.assertEqual(ng.answer(run, "repo-a", 1, "done", note="shipped")["comment"], "Done.\n\nshipped")

    def test_answer_rejects_unknown_repo_and_empty(self) -> None:
        run, _ = runner()
        with self.assertRaises(ng.CommandError):
            ng.answer(run, "other", 1, "text", "x")
        with self.assertRaises(ng.CommandError):
            ng.answer(run, "repo-a", 1, "pick", "")

    def test_failed_comment_keeps_the_label(self) -> None:
        run, _ = runner(dry=False)
        with mock.patch.object(run, "_exec", side_effect=ng.CommandError("boom")) as ex:
            with self.assertRaises(ng.CommandError):
                ng.answer(run, "repo-a", 1, "text", "x")
        self.assertEqual(ex.call_count, 1)

    def test_label_is_configurable(self) -> None:
        run, rec = runner()
        run.cfg.label = "manual"
        ng.answer(run, "repo-a", 1, "done")
        self.assertIn("--remove-label manual", rec.lines[1])

    def _start(self, run, workspaces: list[dict]):
        listing = json.dumps({"result": {"workspaces": workspaces}})
        with mock.patch.object(run, "_exec", return_value=listing):
            return ng.start(run, "repo-a", 12, "haiku", "https://example.com/i/12")

    def test_start_local_uses_herdr_directly(self) -> None:
        run, rec = runner()
        out = self._start(run, [{"workspace_id": "w1", "label": "repo-a"}])
        self.assertEqual(out["tab"], "#12")
        self.assertEqual(rec.lines[0], "DRY herdr tab create --workspace w1 --cwd /x/repo-a --label '#12' --no-focus")
        self.assertIn("herdr agent start repo-a-12 --kind claude --pane '<pane>' -- --model haiku", rec.lines[1])
        self.assertIn("herdr agent prompt repo-a-12", rec.lines[2])
        self.assertIn("unblocked #12 (https://example.com/i/12)", rec.lines[2])

    def test_start_remote_goes_through_ssh(self) -> None:
        run, rec = runner(host="host-b")
        self._start(run, [{"workspace_id": "w1", "label": "repo-a"}])
        self.assertTrue(all(line.startswith("DRY ssh ") for line in rec.lines))
        self.assertIn(" host-b ", rec.lines[0])

    def test_start_creates_missing_workspace(self) -> None:
        run, rec = runner()
        self._start(run, [])
        self.assertIn("herdr workspace create --cwd /x/repo-a --label repo-a --no-focus", rec.lines[0])
        self.assertIn("herdr tab rename", rec.lines[1])

    def test_start_reports_unreachable_host(self) -> None:
        run, _ = runner(host="host-b", dry=False)
        with mock.patch.object(run, "_exec", side_effect=ng.CommandError("no route")):
            with self.assertRaisesRegex(ng.CommandError, "on host-b: no route"):
                ng.start(run, "repo-a", 1, "sonnet")

    def test_real_start_without_pane_id_raises(self) -> None:
        run, _ = runner(dry=False)
        replies = iter([json.dumps({"result": {"workspaces": [{"workspace_id": "w1", "label": "repo-a"}]}}),
                        json.dumps({"result": {}})])
        with mock.patch.object(run, "_exec", side_effect=lambda *a, **k: next(replies)) as ex:
            with self.assertRaisesRegex(ng.CommandError, "no result.root_pane.pane_id"):
                ng.start(run, "repo-a", 1, "sonnet")
        self.assertEqual(ex.call_count, 2)

    def test_start_names_the_folder_trust_prompt(self) -> None:
        run, _ = runner(dry=False)
        listing = json.dumps({"result": {"workspaces": [{"workspace_id": "w1", "label": "repo-a"}]}})
        tab = json.dumps({"result": {"root_pane": {"pane_id": "w1:p2"}}})
        blocked = ng.CommandError('{"error":{"code":"agent_not_ready","message":"blocked during startup"}}')
        replies = iter([listing, tab, blocked])

        def fake(*a, **k):
            r = next(replies)
            if isinstance(r, Exception):
                raise r
            return r
        with mock.patch.object(run, "_exec", side_effect=fake):
            with self.assertRaisesRegex(ng.CommandError, "pane w1:p2 on this host is waiting on its folder-trust"):
                ng.start(run, "repo-a", 1, "sonnet")

    def test_label_failure_says_the_comment_posted(self) -> None:
        run, _ = runner(dry=False)
        with mock.patch.object(run, "_exec", side_effect=["", ng.CommandError("denied")]):
            with self.assertRaisesRegex(ng.CommandError, "comment posted, but removing the label"):
                ng.answer(run, "repo-a", 1, "done")

    def test_image_paths(self) -> None:
        run, _ = runner(dry=False)
        for bad in ("/etc/a.png", "../a.png", "a/../b.png", "a%2e.png", "a?x.png", "a#b.png",
                    "a\\b.png", "pic.svg", "pic", "a.png.sh"):
            with self.assertRaises(ng.CommandError, msg=bad):
                ng.fetch_image(run, "repo-a", bad)
        with mock.patch.object(run, "_exec", return_value=b"\x89PNG"):
            self.assertEqual(ng.fetch_image(run, "repo-a", "art/a b.PNG"), (b"\x89PNG", "image/png"))

    def test_lfs_token_only_goes_to_github_hosts(self) -> None:
        self.assertTrue(ng._trusted_host("https://media.githubusercontent.com/x"))
        self.assertTrue(ng._trusted_host("https://github.com/x"))
        for bad in ("http://github.com/x", "https://evilgithub.com/x", "https://github.com.evil.io/x",
                    "https://example.com/x", ""):
            self.assertFalse(ng._trusted_host(bad), bad)
        run, _ = runner(dry=False)
        replies = [ng.LFS_MAGIC + b"\noid", ]
        with mock.patch.object(run, "_exec", side_effect=replies), \
                mock.patch.object(run, "gh", return_value=json.dumps({"download_url": "https://example.com/x"})):
            with self.assertRaisesRegex(ng.CommandError, "not on a GitHub host"):
                ng.fetch_image(run, "repo-a", "a.png")

    def test_start_rejects_opus_typo(self) -> None:
        run, _ = runner()
        with self.assertRaises(ng.CommandError):
            ng.start(run, "repo-a", 1, "gpt")

    def test_list_asks_falls_back_to_title(self) -> None:
        run, _ = runner()
        issues = [
            {"repository": {"name": "repo-a"}, "number": 2, "title": "Plain", "url": "u2",
             "body": "no block", "createdAt": "2026-01-02T00:00:00Z"},
            {"repository": {"name": "repo-a"}, "number": 1, "title": "Bad", "url": "u1",
             "body": BLOCK.format("ask: x\ntype: pick"), "createdAt": "2026-01-01T00:00:00Z"},
            {"repository": {"name": "elsewhere"}, "number": 3, "title": "Skip", "url": "u3",
             "body": "", "createdAt": "2026-01-03T00:00:00Z"},
        ]
        with mock.patch.object(run, "gh", return_value=json.dumps(issues)):
            asks = ng.list_asks(run)
        self.assertEqual([a["number"] for a in asks], [1, 2])
        self.assertEqual(asks[0]["ask"], "Bad")
        self.assertIn("options", asks[0]["warning"])
        self.assertEqual((asks[1]["ask"], asks[1]["type"]), ("Plain", "text"))


class HttpTest(unittest.TestCase):
    def setUp(self) -> None:
        self.run, self.rec = runner()
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), ng.make_handler(self.run))
        self.base = f"http://127.0.0.1:{self.srv.server_port}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)

    def call(self, path, body=None, headers=None):
        h = {"Tailscale-User-Login": "user@example.com", **(headers or {})}
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, headers=h)
        try:
            with urllib.request.urlopen(req) as r:
                return r.status
        except urllib.error.HTTPError as e:
            e.close()
            return e.code

    def test_wrong_or_missing_login_is_403(self) -> None:
        self.assertEqual(self.call("/", headers={"Tailscale-User-Login": "x@example.com"}), 403)
        req = urllib.request.Request(self.base + "/api/asks")
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req)
        cm.exception.close()
        self.assertEqual(cm.exception.code, 403)

    def test_index_served_to_the_right_login(self) -> None:
        self.assertEqual(self.call("/"), 200)

    def test_unexpected_error_is_json_502(self) -> None:
        with mock.patch.object(ng, "list_asks", side_effect=RuntimeError("kaput")):
            self.assertEqual(self.call("/api/asks"), 502)

    def test_content_length_bounds(self) -> None:
        host = f"127.0.0.1:{self.srv.server_port}"
        big = {"repo": "repo-a", "number": 1, "kind": "text", "text": "x" * 70000}
        self.assertEqual(self.call("/api/answer", big, {"Content-Type": "application/json",
                                                        "Origin": f"http://{host}"}), 413)

    def test_post_needs_same_origin_json(self) -> None:
        body = {"repo": "repo-a", "number": 1, "kind": "done"}
        host = f"127.0.0.1:{self.srv.server_port}"
        self.assertEqual(self.call("/api/answer", body, {"Content-Type": "application/json"}), 403)
        self.assertEqual(self.call("/api/answer", body, {"Content-Type": "application/json",
                                                         "Origin": "http://evil.example"}), 403)
        self.assertEqual(self.call("/api/answer", body, {"Content-Type": "text/plain",
                                                         "Origin": f"http://{host}"}), 415)
        self.assertEqual(self.call("/api/answer", body, {"Content-Type": "application/json",
                                                         "Origin": f"http://{host}"}), 200)
        self.assertEqual(sum(x.startswith("DRY") for x in self.rec.lines), 2)


if __name__ == "__main__":
    unittest.main()
