"""Reading an API key by variable name. The value is returned to the caller and never printed or stored.

Order: the process environment; then, when `asr.key_file` is set, that file and only it (see
`keyfile.py`); otherwise `.env` in the current folder, then the AIEditing config folder
(`~/.aiediting/.env`; Windows: `%LOCALAPPDATA%\\AIEditing\\.env`).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from . import dotenv
from .contract import AsrError
from .keyfile import read_from_key_file


def config_dir() -> Path:
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "AIEditing"
    return Path.home() / ".aiediting"


def _env_files() -> List[Path]:
    return [Path.cwd() / ".env", config_dir() / ".env"]


def read_key(name: str, key_file: Optional[str] = None) -> str:
    """The key stored under `name`; AsrError naming only the variable (and the file) if it is absent."""
    value = os.environ.get(name)
    if value:
        return value
    if key_file:
        return read_from_key_file(name, key_file)
    for path in _env_files():
        value = dotenv.value_in(path, name)
        if value:
            return value
    raise AsrError(
        "Не найден ключ: переменная {0} не задана. Впишите строку {0}=… в файл .env "
        "(в папке, где идёт работа, или в {1}) — в чат ключ не присылайте.".format(name, config_dir())
    )
