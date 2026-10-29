"""Reading an API key by variable name. The value is returned to the caller and never printed or stored.

Order: the process environment, then `asr.key_file` (a .env the person already keeps the key in) when it
is set, then `.env` in the current folder, then the AIEditing config folder (`~/.aiediting/.env`;
Windows: `%LOCALAPPDATA%\\AIEditing\\.env`). The key is read at run time and copied nowhere.
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


def _lines(path: Path) -> Optional[List[str]]:
    try:
        return path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeDecodeError):
        return None


def _from_file(path: Path, name: str) -> Optional[str]:
    for line in _lines(path) or []:
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


def _key_file_problem(path: Path, name: str) -> str:
    if not path.is_file():
        return "файла {} нет".format(path)
    if _lines(path) is None:
        return "файл {} не читается".format(path)
    return "в файле {} нет строки {}=…".format(path, name)


def read_key(name: str, key_file: Optional[str] = None) -> str:
    """The key stored under `name`; AsrError naming only the variable and the file if it is absent."""
    value = os.environ.get(name)
    named = Path(key_file).expanduser().absolute() if key_file else None
    for path in ([named] if named else []) + _env_files():
        if value:
            break
        value = _from_file(path, name)
    if value:
        return value
    if named:
        raise AsrError(
            "Не найден ключ {}: {} (это asr.key_file в профиле). Проверьте путь и имя переменной; "
            "ключ в чат не присылайте.".format(name, _key_file_problem(named, name)))
    raise AsrError(
        "Не найден ключ: переменная {0} не задана. Впишите строку {0}=… в файл .env "
        "(в папке, где идёт работа, или в {1}) — в чат ключ не присылайте.".format(name, config_dir())
    )
