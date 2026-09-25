This is a small click todo app (src/todo/). Add two features, with tests:

1. `todo done ID` marks item ID done and prints `done ID`. An unknown ID prints
   `no item ID` and exits with status 1.
2. `todo list --pending` shows only items that are not done.

Also fix this bug: after deleting items from todo.json by hand, `add` can reuse
an existing id. New ids must be one more than the highest existing id.

Keep the existing output formats. pyproject.toml is already correct: do not
edit it. You are done when `uv run pytest` passes.
