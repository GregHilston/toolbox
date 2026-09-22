Create a tiny greeting module and complete the card
This card exists to exercise the completion gate, not to build anything useful. Keep it minimal.

Create exactly two files under /instance/workspace:

1. src/vt_smb/hello.py with a function `hello()` that returns the string "hi".
2. src/vt_smb/cli.py with a click group named `main`, so the `vt-smb` console script imports. Give it one subcommand `greet` that prints hello().

Then create tests/test_hello.py asserting hello() == "hi".

Do not create anything else. Do not edit pyproject.toml.

DONE WHEN all three hold:
1. `uv run pytest` passes with zero failures
2. `uv run vt-smb --help` exits 0
3. src/vt_smb/hello.py and tests/test_hello.py both exist
