"""`asr.key_file`: a .env the person already keeps the key in. Read at run time, copied nowhere.

The field holds a path, never a key: a value that does not look like a path is refused, and no message
ever repeats it (a key pasted there by mistake must not reach the chat or a log). A set `key_file` is
the only file looked at: no silent fallback to another `.env`.
"""
from __future__ import annotations

from pathlib import Path

from . import dotenv
from .contract import AsrError

NOT_A_PATH = ("asr.key_file: это не похоже на путь к файлу (нужен путь вида ~/папка/.env); "
              "значение не показываю — если туда попал сам ключ, уберите его из профиля")


def looks_like_path(text: object) -> bool:
    """A path has a separator or starts with `~`, `/` or `.`; a bare word (a pasted key) does not."""
    if not isinstance(text, str) or not text.strip():
        return False
    return "/" in text or "\\" in text or text.startswith(("~", "."))


def read_from_key_file(name: str, key_file: str) -> str:
    """The value of `name` from `key_file`; AsrError naming the file and the variable, never a value."""
    if not looks_like_path(key_file):
        raise AsrError("Не найден ключ {}: {}.".format(name, NOT_A_PATH))
    path = Path(key_file).expanduser().absolute()
    value = dotenv.value_in(path, name)
    if value:
        return value
    if not path.is_file():
        problem = "файла {} нет".format(path)
    elif dotenv.lines(path) is None:
        problem = "файл {} не читается".format(path)
    else:
        problem = "в файле {} нет строки {}=…".format(path, name)
    raise AsrError("Не найден ключ {}: {} (это asr.key_file в профиле). Проверьте путь и имя переменной; "
                   "ключ в чат не присылайте.".format(name, problem))
