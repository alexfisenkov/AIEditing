"""Moments worth an animated insert, found in what is said: files, steps, a number with its unit, a list.

A draft only: the person corrects the template, the heading and the points, or drops the moment.
RANK orders them when two compete for one window (anim_slots): files > steps > a number > a list.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence

from .filenames import FILE, file_items
from .listing import chunks, items, listed
from .points import ITEM_WORDS, content
from .words import quote

RANK = {"файлы": 4, "шаги": 3, "число": 2, "список": 1}
_FILES = re.compile(r"^(файл\w*|документ\w*|files?)$", re.I)
_STEPS = re.compile(r"^(шаг\w*|этап\w*|сначала|во-первых|steps?|first)$", re.I)
_NUMBER = re.compile(r"^\d+(?:[.,]\d+)?(%|[kкKК])?$")
_UNIT = re.compile(r"^(процент\w*|тысяч\w*|миллион\w*|миллиард\w*|раз|раза|рубл\w*|доллар\w*|евро|минут\w*|"
                   r"секунд\w*|час\w*|дн\w*|день|недел\w*|месяц\w*|лет|год\w*|токен\w*|гигабайт\w*|мегабайт\w*|"
                   r"гб|мб|тб|кб|percent|thousand|million|billion|times|hours?|minutes?|days?|tokens?)$", re.I)


def _number(words: List[str]) -> Optional[Dict]:
    """A figure with a unit (%, тысяч, минут…): bare figures are counts in passing, not a moment."""
    for k, w in enumerate(words):
        m = _NUMBER.match(w)
        if not m:
            continue
        rest = words[k + 1:]
        if m.group(1):
            value = w
        elif rest and _UNIT.match(rest[0]):
            value = w + ("%" if rest[0].lower().startswith("процент") else " " + rest[0])
            rest = rest[1:]
        else:
            continue
        caption = content(rest[:ITEM_WORDS + 2])
        return {"template": "число", "title": value, "items": [" ".join(caption[:ITEM_WORDS])] if caption else []}
    return None


def detect(phrase: Dict) -> Optional[Dict]:
    """{template, title, items} for one phrase, or None."""
    lead, parts = chunks(phrase["words"])
    flat = lead + [w for c in parts for w in c]
    trigger = _FILES if any(_FILES.match(w) for w in flat) else None
    names = file_items([lead] + parts if lead else parts, trigger)
    named = sum(1 for n in names if FILE.match(n))
    if named >= 2 or (trigger and (named and len(names) >= 2 or len(names) >= 3)):
        return {"template": "файлы", "title": "Файлы", "items": names}
    if len(parts) >= 2:
        steps = any(_STEPS.match(w) for w in flat)
        points = items(parts, _STEPS if steps else None)
        if steps and len(points) >= 2:
            return {"template": "шаги", "title": "Шаги", "items": points}
        number, points = _number(flat), listed(parts)
        if number or not points:
            return number
        return {"template": "список", "title": "", "items": points}
    return _number(flat)


def find(phrases: Sequence[Dict]) -> List[Dict]:
    """Every phrase that holds an insert: [{start, template, title, items, said}] in time order."""
    out = []
    for p in phrases:
        found = detect(p)
        if found:
            out.append(dict(found, start=round(p["start"], 3), said=quote(p["words"])))
    return out
