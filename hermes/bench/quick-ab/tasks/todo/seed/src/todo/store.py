import json
from pathlib import Path


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text())


def save(path: Path, items: list[dict]) -> None:
    path.write_text(json.dumps(items, indent=2))
