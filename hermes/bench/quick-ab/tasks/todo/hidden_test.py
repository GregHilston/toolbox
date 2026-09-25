import json
from click.testing import CliRunner
from todo.cli import main

def run(f, *args):
    return CliRunner().invoke(main, ["--file", f, *args])

def test_done(tmp_path):
    f = str(tmp_path / "t.json")
    run(f, "add", "a"); run(f, "add", "b")
    r = run(f, "done", "2")
    assert r.exit_code == 0 and r.output == "done 2\n"
    assert run(f, "list").output == "[ ] 1 a\n[x] 2 b\n"

def test_done_unknown(tmp_path):
    f = str(tmp_path / "t.json")
    run(f, "add", "a")
    r = run(f, "done", "9")
    assert r.exit_code == 1 and "no item 9" in r.output

def test_pending(tmp_path):
    f = str(tmp_path / "t.json")
    run(f, "add", "a"); run(f, "add", "b"); run(f, "done", "1")
    assert run(f, "list", "--pending").output == "[ ] 2 b\n"

def test_id_after_manual_delete(tmp_path):
    p = tmp_path / "t.json"
    p.write_text(json.dumps([{"id": 1, "text": "a", "done": False},
                             {"id": 3, "text": "c", "done": False}]))
    assert run(str(p), "add", "d").output == "added 4\n"

def test_existing_formats(tmp_path):
    f = str(tmp_path / "t.json")
    assert run(f, "add", "milk").output == "added 1\n"
    assert run(f, "list").output == "[ ] 1 milk\n"
