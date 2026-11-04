"""The data of a vertical cut (src/vertical/spans.json): reading, checking, lengths of clips, seconds of frames.

Lengths follow src/vertical/clips.ts exactly: the speech of a clip is the sum of its spans divided by `rate`,
the call to action appears `cta_lead` before the speech ends and the clip lasts `cta_tail` longer than the speech.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .common import FPS, ToolError

CLIP_ID = re.compile(r"^c\d+$")
BAD_NAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
CTA_KEYS = ("lead", "before", "word", "after")
# Text zones (x0, y0, x1, y1) of 1080x1920 by platform. The same numbers stand in template/src/vertical/safe.ts; a test keeps them equal.
SAFE_ZONES: Dict[str, Tuple[int, int, int, int]] = {"reels": (70, 270, 940, 1240)}
RATE_RANGE = (0.5, 2.0)  # the range of ffmpeg's atempo that stays one filter
SOURCE_TOLERANCE = 0.35  # seconds between source_seconds and the real length of the file
APPEAR = 0.4  # seconds the curtain of the call takes to become opaque (the ease of 0.35 s plus a margin)


def js_round(value: float) -> int:
    """Math.round of JavaScript for the values here (never negative): halves go up."""
    return int(value + 0.5)


def load(path: Path) -> Dict:
    """spans.json as a dictionary, or a ToolError that says what is wrong with it."""
    path = Path(path).expanduser()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ToolError("Не читается {}: {}".format(path, exc))
    except ValueError as exc:
        raise ToolError("{} не разобрать как JSON: {}".format(path, exc))
    check(data, path.name)
    return data


def has_cta(data: Dict) -> bool:
    """A call to action exists when `cta` carries at least one word. null, {} or blank words mean the clip has none."""
    cta = data.get("cta")
    return isinstance(cta, dict) and any(isinstance(cta.get(k), str) and cta[k].strip() for k in CTA_KEYS)


def lead(data: Dict) -> float:
    return float(data.get("cta_lead", 0) or 0) if has_cta(data) else 0.0


def tail(data: Dict) -> float:
    return float(data.get("cta_tail", 0) or 0) if has_cta(data) else 0.0


def check(data: Dict, label: str = "spans.json") -> None:
    def bad(text: str):
        raise ToolError("{}: {}".format(label, text))

    if not isinstance(data, dict):
        bad("ожидался объект JSON.")
    rate = data.get("rate")
    if not isinstance(rate, (int, float)) or isinstance(rate, bool) or not RATE_RANGE[0] <= rate <= RATE_RANGE[1]:
        bad("rate — число от {} до {} (скорость речи относительно файла, который лежит в public/clips/source.mp4).".format(*RATE_RANGE))
    cta = data.get("cta")
    if has_cta(data):
        if not isinstance(cta, dict) or any(not isinstance(cta.get(k), str) for k in CTA_KEYS):
            bad('cta — объект со строками {}: слова призыва (пустая строка скрывает строку).'.format(", ".join(CTA_KEYS)))
        for key in ("cta_lead", "cta_tail"):
            value = data.get(key)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                bad("{} — число секунд, не меньше нуля.".format(key))
        if data["cta_tail"] < 0.5:
            bad("cta_tail меньше 0,5 с: призыв не успеют прочитать.")
    else:  # a clip without a call is the person's choice: then there is no lead and no tail
        for key in ("cta_lead", "cta_tail"):
            if data.get(key, 0) not in (0, 0.0):
                bad("призыва нет (cta пустой или null), поэтому {} должен быть 0 или отсутствовать.".format(key))
        if cta is not None and not isinstance(cta, dict):
            bad("cta — объект со строками {} или null.".format(", ".join(CTA_KEYS)))
    seconds = data.get("source_seconds")
    if seconds is not None and (not isinstance(seconds, (int, float)) or isinstance(seconds, bool) or seconds <= 0):
        bad("source_seconds — длина файла public/clips/source.mp4 в секундах (число больше нуля) или его нет.")
    if data.get("safe", "reels") not in SAFE_ZONES:
        bad("safe — одно из: {}.".format(", ".join(sorted(SAFE_ZONES))))
    spans, names = data.get("spans"), data.get("names", {})
    if not isinstance(spans, dict) or not spans:
        bad("spans — объект «клип: список отрезков», ни одного клипа нет.")
    for cid, rows in spans.items():
        if not CLIP_ID.match(cid):
            bad("имя клипа «{}» не подходит: c и число, например c1.".format(cid))
        if not isinstance(rows, list) or not rows:
            bad("у клипа {} нет отрезков.".format(cid))
        for row in rows:
            ok = isinstance(row, list) and len(row) == 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in row)
            if not ok or row[0] < 0 or row[1] <= row[0]:
                bad("отрезок {} в клипе {}: нужна пара [начало, конец] в секундах, конец позже начала.".format(row, cid))
    if not isinstance(names, dict):
        bad("names — объект «клип: имя файла».")
    for cid, name in names.items():
        if cid not in spans:
            bad("в names есть {}, а отрезков у него нет.".format(cid))
        if not isinstance(name, str) or not name.strip() or BAD_NAME.search(name) or name != name.strip() or name.endswith("."):
            bad("имя файла клипа {} не подходит: {!r} (без / \\ : * ? \" < > |, без пробелов по краям).".format(cid, name))
    seen: Dict[str, str] = {}
    for cid in spans:  # the name a clip's file gets: on APFS and NTFS names that differ only in case or form are one file
        key = unicodedata.normalize("NFC", clip_name(data, cid)).casefold()
        if key in seen:
            bad("клипы {} и {} получают одно имя файла «{}» (регистр и форма символов не различаются на APFS и NTFS): один затрёт другой."
                .format(seen[key], cid, clip_name(data, cid)))
        seen[key] = cid
    small = data.get("small_ok", [])
    if not isinstance(small, list) or any(not isinstance(s, str) for s in small):
        bad("small_ok — список строк.")


def clip_ids(data: Dict) -> List[str]:
    return sorted(data["spans"], key=lambda c: int(c[1:]))


def clip_name(data: Dict, cid: str) -> str:
    return data.get("names", {}).get(cid) or cid


def speech_seconds(data: Dict, cid: str) -> float:
    return sum(b - a for a, b in data["spans"][cid]) / data["rate"]


def speech_frames(data: Dict, cid: str) -> int:
    return js_round(speech_seconds(data, cid) * FPS)


def clip_frames(data: Dict, cid: str) -> int:
    """Frames of the finished clip: the speech and the tail after it (the call overlaps the last cta_lead seconds of the speech)."""
    return speech_frames(data, cid) + js_round(tail(data) * FPS)


def clip_seconds(data: Dict, cid: str) -> float:
    return clip_frames(data, cid) / FPS


def cta_start(data: Dict, cid: str) -> Optional[float]:
    """Seconds of the clip at which the call to action appears; None for a clip without a call."""
    if not has_cta(data):
        return None
    return max(0.0, speech_seconds(data, cid) - lead(data))


def cta_needed(data: Dict) -> float:
    """Seconds the call must be fully visible at the end: lead and tail less the time it takes to appear. 0 without a call."""
    return max(0.0, lead(data) + tail(data) - APPEAR) if has_cta(data) else 0.0


def check_source_seconds(data: Dict, have: float) -> None:
    """`source_seconds` (written by the tool that cut the clips) must be the length of the file the clips are cut from."""
    want = data.get("source_seconds")
    if want is not None and abs(want - have) > SOURCE_TOLERANCE:
        raise ToolError("spans.json писали под файл длиной {:.2f} с, а public/clips/source.mp4 длится {:.2f} с (допуск {:g} с). "
                        "Это другая запись или она перемонтирована: секунды отрезков не совпадут с речью. Пересчитайте spans.json под этот файл."
                        .format(want, have, SOURCE_TOLERANCE))


def check_against_source(data: Dict, source_seconds: float, cids: Optional[List[str]] = None) -> None:
    """Every span lies inside the file the clips are cut from."""
    for cid in cids or clip_ids(data):
        for a, b in data["spans"][cid]:
            if b > source_seconds + 0.05:
                raise ToolError("Клип {}: отрезок {}–{} с выходит за конец видео ({:.2f} с). Секунды берите из файла public/clips/source.mp4."
                                .format(cid, a, b, source_seconds))


def frame_seconds(frame: int, fps: float = FPS) -> float:
    """The second of a frame of a clip. Sheets get their labels from here and from nothing else."""
    return frame / fps
