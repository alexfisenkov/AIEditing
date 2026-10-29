"""Moments worth an animated insert, found in what is said: files, steps, a list of points, a number.

A draft only: the person corrects the template, the heading and the points, or drops the moment.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence

from .listing import ITEM_WORDS, MAX_ITEMS, chunks, items
from .words import quote

_FILE = re.compile(r"^[\w-]+\.[a-z][a-z0-9]{0,4}$", re.I)         # agents.md, run.py, tokens.json
_FILES = re.compile(r"^(файл\w*|документ\w*|files?)$", re.I)
_STEPS = re.compile(r"^(шаг\w*|этап\w*|сначала|во-первых|steps?|first)$", re.I)
_NUMBER = re.compile(r"^\d+(?:[.,]\d+)?%?$")


def _number(words: List[str]) -> Optional[Dict]:
    at = next((k for k, w in enumerate(words) if _NUMBER.match(w)), None)
    if at is None:
        return None
    value, rest = words[at], words[at + 1:]
    if rest and rest[0].lower().startswith("процент") and not value.endswith("%"):
        value, rest = value + "%", rest[1:]
    return {"template": "число", "title": value, "items": [" ".join(rest[:ITEM_WORDS])] if rest else []}


def detect(phrase: Dict) -> Optional[Dict]:
    """{template, title, items} for one phrase, or None. Files beat steps, steps beat a list, a list a number."""
    lead, parts = chunks(phrase["words"])
    flat = lead + [w for c in parts for w in c]
    files = any(_FILE.match(w) for w in flat) or any(_FILES.match(w) for w in flat)
    steps = any(_STEPS.match(w) for w in flat)
    named = [w for w in flat if _FILE.match(w)]
    if len(named) >= 2 and len(parts) < 2:  # «кладём CLAUDE.md и README.md рядом»
        return {"template": "файлы", "title": "Файлы", "items": named[:MAX_ITEMS]}
    if len(parts) >= 2:
        trigger = _FILES if files else _STEPS if steps else None
        points = items(parts, trigger)
        if files and len(points) >= 2:
            return {"template": "файлы", "title": "Файлы", "items": points}
        if steps and len(points) >= 2:
            return {"template": "шаги", "title": "Шаги", "items": points}
        if len(points) >= 3:
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
