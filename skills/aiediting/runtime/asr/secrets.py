"""Reading an API key by variable name. The value is returned to the caller and never printed.

Order: the process environment, then `.env` in the current folder, then the AIEditing config folder
(`~/.aiediting/.env`; Windows: `%LOCALAPPDATA%\\AIEditing\\.env`).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from .contract import AsrError


def config_dir() -> Path:
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "AIEditing"
    return Path.home() / ".aiediting"


def _env_files() -> List[Path]:
    return [Path.cwd() / ".env", config_dir() / ".env"]


def _from_file(path: Path, name: str) -> Optional[str]:
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return None
    for line in lines:
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


def read_key(name: str) -> str:
    """The key stored under `name`; AsrError naming only the variable if it is absent."""
    value = os.environ.get(name)
    for path in _env_files():
        if value:
            break
        value = _from_file(path, name)
    if not value:
        raise AsrError(
            "Не найден ключ: переменная {0} не задана. Впишите строку {0}=… в файл .env "
            "(в папке, где идёт работа, или в {1}) — в чат ключ не присылайте.".format(name, config_dir())
        )
    return value
