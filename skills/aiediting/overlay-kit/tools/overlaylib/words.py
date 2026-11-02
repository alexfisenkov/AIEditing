"""The words file: lines "%7.2f word", seconds of the passed video. Checked, then copied to raw/words.txt."""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import List, Tuple

from .common import ToolError

LINE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s+(\S.*?)\s*$")
SLACK = 1.5  # words may end this much after the picture; more means the file belongs to another recording


def read_words(path: Path) -> List[Tuple[float, str]]:
    if not Path(path).is_file():
        raise ToolError("Нет файла слов: {}".format(path))
    words = []
    for number, line in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        found = LINE.match(line)
        if not found:
            raise ToolError("Файл слов, строка {}: ожидается «секунда слово» (например «  12.40 привет»), а там: {}".format(number, line[:60]))
        words.append((float(found.group(1)), found.group(2)))
    if not words:
        raise ToolError("Файл слов пуст: {}".format(path))
    return words


def check_words(src: Path, duration: float) -> int:
    """Format and range, before anything is written; returns the number of words."""
    words = read_words(src)
    last = max(t for t, _ in words)
    if last > duration + SLACK:
        raise ToolError("Слова доходят до {:.1f} с, а видео длится {:.1f} с. Время слов — секунды ЭТОГО видео "
                        "(после нарезки пересчитайте слова на новый хронометраж).".format(last, duration))
    return len(words)


def install_words(src: Path, duration: float, work: Path) -> int:
    count = check_words(src, duration)
    raw = work / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    dst = raw / "words.txt"
    if Path(src).resolve() != dst.resolve():
        tmp = raw / "words.txt.part"
        shutil.copyfile(str(src), str(tmp))
        os.replace(str(tmp), str(dst))
    return count
