from click.testing import CliRunner

from todo.cli import main


def test_add_and_list(tmp_path):
    f = str(tmp_path / "t.json")
    r = CliRunner()
    assert r.invoke(main, ["--file", f, "add", "milk"]).output == "added 1\n"
    assert r.invoke(main, ["--file", f, "list"]).output == "[ ] 1 milk\n"
