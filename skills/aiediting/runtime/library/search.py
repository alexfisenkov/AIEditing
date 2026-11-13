"""Candidates for an insert under a phrase: words of the inventory against the words of the phrase.

No embeddings and no model, so it runs on any computer; the final choice stays with the agent.
Word forms are matched by a short stem, so «моря» finds «море» and «Петю» names «Петя».
"""
from __future__ import annotations

import re
from typing import Iterable, List, Optional, Set

_WORD = re.compile(r"\w+", re.UNICODE)
_STOP = {"это", "как", "что", "так", "там", "тут", "вот", "где", "для", "или", "был", "была", "были", "мой",
         "моя", "мои", "наш", "она", "они", "его", "the", "and", "with", "this", "that"}
WEIGHTS = (("phrases", 3), ("tags", 2), ("who", 2), ("what", 1), ("where", 1))


def _stem(word: str) -> str:
    """The first letters of a word: five of a long one, all but the ending of a short one."""
    word = word.casefold()
    return word[:5] if len(word) > 5 else word[:max(3, len(word) - 1)]


def _same(a: str, b: str) -> bool:
    return a.startswith(b) or b.startswith(a)


def _hits(phrase: Set[str], field: Set[str]) -> int:
    return sum(1 for p in phrase if any(_same(p, f) for f in field))


def stems(text) -> Set[str]:
    words = _WORD.findall(" ".join(text) if isinstance(text, (list, tuple)) else str(text or ""))
    return {_stem(w) for w in words if len(w) >= 3 and not w.isdigit() and w.casefold() not in _STOP}


def _year(row: dict) -> Optional[int]:
    date = str(row.get("date") or "")
    return int(date[:4]) if date[:4].isdigit() else None


def blocked(row: dict, forbidden: Iterable[str]) -> bool:
    """A row whose person, tag or file is named in the never list (any word form of a name)."""
    names = list(row.get("who") or []) + list(row.get("tags") or [])
    for entry in forbidden:
        said = stems(entry)
        if str(entry).strip().casefold() == str(row.get("f", "")).casefold():
            return True
        for name in names:
            mine = stems(name)
            if mine and _hits(mine, said) == len(mine):
                return True
    return False


def score(row: dict, phrase: Set[str]) -> int:
    return sum(weight * _hits(phrase, stems(row.get(field) or "")) for field, weight in WEIGHTS)


def candidates(rows: List[dict], phrase: str, year: Optional[int], limit: int = 5,
               forbidden: Iterable[str] = ()) -> List[dict]:
    """Best rows for `phrase`, each with its "score"; never-rows and the never list are left out.

    A year named by the phrase goes first: rows of that year, then undated ones, then other years."""
    words, forbidden = stems(phrase), list(forbidden)
    found = []
    for i, row in enumerate(rows):
        if row.get("never") or blocked(row, forbidden):
            continue
        points = score(row, words)
        if points <= 0:
            continue
        when = _year(row)
        place = 0 if year is None or when == year else (1 if when is None else 2)
        found.append((place, -points, i, dict(row, score=points)))
    return [item[-1] for item in sorted(found, key=lambda x: x[:3])[:max(0, limit)]]
