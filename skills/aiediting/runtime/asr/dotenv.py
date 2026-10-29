"""Reading one variable from a `.env` file: `NAME=value`, `export NAME=value`, quotes stripped."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional


def lines(path: Path) -> Optional[List[str]]:
    """The file's lines, or None when it is missing or unreadable."""
    try:
        return path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeDecodeError):
        return None


def value_in(path: Path, name: str) -> Optional[str]:
    for line in lines(path) or []:
        line = line.strip()
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, sep, value = line.partition("=")
        if sep and key.strip() == name:
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1]
            return value or None
    return None
