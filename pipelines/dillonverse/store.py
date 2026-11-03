from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def upsert(path: Path, additions: list[dict[str, Any]], key: str = "video_id") -> None:
    current = {str(row[key]): row for row in read_jsonl(path) if row.get(key) is not None}
    for row in additions:
        current[str(row[key])] = row
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in current.values()),
        encoding="utf-8",
    )
