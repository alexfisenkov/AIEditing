"""The time map of a long video that was edited by markers (src/data/time-map.json), and the words of a clip in all three kinds of seconds.

Three kinds of seconds meet in a vertical clip of such a folder:
  file   seconds of public/clips/source.mp4 and raw/words.txt: what `spans.json` holds
  scene  what the scenes use: scene = toOld(file), and file = toNew(scene) (src/kit/time.ts)
  clip   seconds of the finished vertical clip
Without a map (an empty one) file and scene seconds are the same.
"""
from __future__ import annotations

import bisect
import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from . import vspans
from .common import ToolError

FACE_STEP = 0.5  # seconds between the rows of src/data/face.json
Row = Sequence[float]  # new start, new end, old start, old end, lead


def load_rows(work: Path) -> List[Row]:
    path = work / "src" / "data" / "time-map.json"
    if not path.is_file():
        return []
    try:
        rows = json.loads(path.read_text(encoding="utf-8")).get("rows", [])
    except (OSError, ValueError, AttributeError):
        raise ToolError("Не читается {}.".format(path))
    return [r for r in rows if isinstance(r, list) and len(r) == 5]


def face_track_seconds(work: Path) -> Optional[float]:
    """Seconds the face track covers (its last row), or None when there is no readable track."""
    path = work / "src" / "data" / "face.json"
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
        return float(rows[-1][0]) if rows else None
    except (OSError, ValueError, IndexError, TypeError):
        return None


def to_old(rows: Sequence[Row], n: float) -> float:
    """src/kit/time.ts toOld: seconds of the file -> seconds of the scenes."""
    if not rows:
        return n
    i = max(0, bisect.bisect_right([r[0] for r in rows], n) - 1)
    r = rows[i]
    return min(r[3], r[2] + max(0.0, n - r[0] - r[4]))


def to_new(rows: Sequence[Row], o: float) -> float:
    """src/kit/time.ts toNew: seconds of the scenes -> seconds of the file (a cut-out second moves to the start of the next piece)."""
    if not rows:
        return o
    for r in rows:
        if r[2] <= o < r[3]:
            return r[0] + r[4] + (o - r[2])
    nxt = next((r for r in rows if r[2] >= o), None)
    return nxt[0] if nxt else rows[-1][1]


def explain(rows: Sequence[Row]) -> str:
    return ("В src/data/time-map.json есть правки по маркерам ({} кусков). Сцены этой папки живут в СТАРЫХ секундах: сцена = toOld(секунда файла), "
            "а spans.json и слова raw/words.txt — в секундах файла public/clips/source.mp4. Раскладку спикера (keys) и at/out в c<N>.tsx пишите "
            "в секундах сцены; границы отрезков в spans.json — в секундах файла. Пересчёт: сцена = toOld(файл), файл = toNew(сцена) "
            "(src/kit/time.ts). Слова клипа во всех трёх секундах печатает overlay.py vertical-words <папка>.").format(len(rows))


def clip_second(data: Dict, cid: str, file_second: float) -> Optional[float]:
    """Seconds of the finished clip at which the file's second is heard; None when no span of the clip holds it."""
    done = 0.0
    for a, b in data["spans"][cid]:
        if a <= file_second < b:
            return (done + file_second - a) / data["rate"]
        done += b - a
    return None


def read_words(path: Path) -> List[Tuple[float, str]]:
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        head, _, word = raw.strip().partition(" ")
        try:
            out.append((float(head), word.strip()))
        except ValueError:
            continue
    return out


def words_file(work: Path, given: Optional[str]) -> Path:
    """The words: the file given with --words, else raw/words.txt. The words are in seconds of the file."""
    path = Path(given).expanduser() if given else work / "raw" / "words.txt"
    if not path.is_file():
        raise ToolError("Нет файла слов {}. Слова клипа берутся из raw/words.txt, а в папке длинного ролика его может не быть: "
                        "передайте файл слов в секундах файла public/clips/source.mp4 через --words <файл> "
                        "(например слова-таймкоды.txt из папки выпуска).".format(path))
    return path


def check_words_fit(words: List[Tuple[float, str]], rows: Sequence[Row], source_seconds: float) -> None:
    """With a time map, words later than the end of the file are words in the OLD seconds: using them would quietly pick the wrong words."""
    if rows and words and words[-1][0] > source_seconds + 1.0:
        raise ToolError("Папка с картой времени, и последнее слово файла слов на {:.1f} с, а public/clips/source.mp4 длится {:.1f} с. "
                        "Это слова в старых секундах сцен. Нужны слова в секундах файла (после правок по маркерам).".format(words[-1][0], source_seconds))


def clip_words(words: List[Tuple[float, str]], rows: Sequence[Row], data: Dict, cid: str) -> List[Tuple[float, float, float, str]]:
    """[(clip second, file second, scene second, word)] for the words that fall inside the spans of the clip."""
    found = []
    for t, word in words:
        c = clip_second(data, cid, t)
        if c is not None:
            found.append((c, t, to_old(rows, t), word))
    return found
