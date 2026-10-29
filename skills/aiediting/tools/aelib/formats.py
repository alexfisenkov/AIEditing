"""The answer to «which formats?»: numbers or words from the list, and your own through commas."""
from __future__ import annotations

import json
import re
from typing import List, Optional

from .paths import CATALOG_DIR

PREFIX = "монтаж-"
_SPLIT = re.compile(r"[,;\n]+|\s+и\s+|\s+and\s+", re.I)
_BAD = re.compile(r"[/\\:*?\"<>|]+")


def load_formats() -> List[dict]:
    data = json.loads((CATALOG_DIR / "formats.json").read_text(encoding="utf-8"))
    return data["formats"]


def format_word(text: str) -> str:
    """«Живой эфир» → «живой-эфир»: lower case, hyphens instead of spaces, no path characters."""
    word = _BAD.sub("", text.strip().lower())
    word = re.sub(r"[\s_]+", "-", word).strip("-.")
    return word[len(PREFIX):] if word.startswith(PREFIX) else word


def skill_name(word: str) -> str:
    return PREFIX + format_word(word)


def _entry(word: str, known: Optional[dict]) -> dict:
    if known:
        return {"id": known["id"], "word": known["word"], "title": known["title"],
                "preset": known["preset"], "skill": skill_name(known["word"]), "custom": False}
    return {"id": "custom", "word": word, "title": word, "preset": "custom",
            "skill": skill_name(word), "custom": True}


def _match(token: str, formats: List[dict]) -> Optional[dict]:
    key = format_word(token)
    for f in formats:
        if key in (f["id"], format_word(f["word"]), format_word(f["title"])):
            return f
    return None


def parse_answer(answer: str, formats: Optional[List[dict]] = None) -> List[dict]:
    """[{"id","word","title","preset","skill","custom"}] in the order named, without repeats."""
    formats = formats if formats is not None else load_formats()
    out, seen = [], set()
    for raw in _SPLIT.split(answer or ""):
        token = re.sub(r"^\s*\d+[.)]\s+", "", raw).strip()
        if not format_word(token):
            continue
        if token.isdigit():
            n = int(token)
            if not 1 <= n <= len(formats):
                raise ValueError("В списке форматов нет пункта {} — есть 1–{}.".format(n, len(formats)))
            item = _entry(formats[n - 1]["word"], formats[n - 1])
        else:
            item = _entry(format_word(token), _match(token, formats))
        if item["skill"] not in seen:
            seen.add(item["skill"])
            out.append(item)
    if not out:
        raise ValueError("Не услышал ни одного формата: назовите из списка или свои через запятую.")
    return out
