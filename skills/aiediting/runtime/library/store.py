"""Atomic reads and writes of the library's files: text, JSON and JSON Lines."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable, List


def write_text(path: Path, text: str) -> Path:
    """The whole file at once through a temporary neighbour, so a crash never leaves half a file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(str(tmp), str(path))
    return path


def read_json(path: Path, default):
    path = Path(path)
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8") or "null") or default
    except ValueError:
        return default


def write_json(path: Path, data) -> Path:
    return write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def read_jsonl(path: Path) -> List[dict]:
    """Rows of a JSON Lines file; a broken line (a crash mid-append) is skipped, not fatal."""
    path = Path(path)
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _line(row: dict) -> str:
    return json.dumps(row, ensure_ascii=False, sort_keys=False)


def write_jsonl(path: Path, rows: Iterable[dict]) -> Path:
    return write_text(path, "".join(_line(r) + "\n" for r in rows))


def append_jsonl(path: Path, rows: Iterable[dict]) -> None:
    """Adds rows to the end without reading the file: a batch at a time, the earlier batches stay."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(_line(row) + "\n")
