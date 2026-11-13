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


# Words of a ban that say «don't», not «whom»: «Петю не брать», «кадры с пляжа никогда не ставить».
_BAN_WORDS = {"не", "ни", "без", "брать", "бери", "берём", "берем", "ставить", "ставь", "показывать", "показывай",
              "нельзя", "никогда", "больше", "кадры", "кадров", "фото", "видео", "замени", "заменить", "с", "со",
              "и", "на", "в", "во", "у", "к", "по", "от", "из"}


def _words(text) -> List[str]:
    """Every word of a name or a ban, two letters and up: «Ян» is a name too; ё is е («Пётр» is «Петр»)."""
    found = _WORD.findall(" ".join(text) if isinstance(text, (list, tuple)) else str(text or ""))
    return [w.casefold().replace("ё", "е") for w in found if len(w) >= 2 and not w.isdigit()]


# A name that drops its vowel in the other cases: «Павел» → «Павла», «Лев» → «Льва»; and the endings of those cases.
_FLEETING = ("ел", "ев", "ец", "ок", "ек")
_CASE_ENDINGS = {"а", "я", "у", "ю", "е", "ы", "и", "ом", "ем", "ой", "ей"}


def _fleeting(base: str, other: str) -> bool:
    """`other` is `base` in another case with its fleeting vowel gone (and a soft sign in its place after a consonant)."""
    if len(base) < 3 or not base.endswith(_FLEETING):
        return False
    stems = (base[:-2] + base[-1], base[:-2] + "ь" + base[-1])
    return any(other.startswith(s) and other[len(s):] in _CASE_ENDINGS for s in stems)


def _form(a: str, b: str) -> bool:
    """Two forms of one word: «Петя»/«Петю», «пляж»/«пляжа», «Павел»/«Павла» — an ending apart, never «Петя»/«Петербург»."""
    if a == b or _fleeting(a, b) or _fleeting(b, a):
        return True
    short, long_ = sorted((a, b), key=len)
    if len(long_) - len(short) > 2:
        return False
    same = 0
    while same < len(short) and short[same] == long_[same]:
        same += 1
    return same >= max(2, len(short) - 1) and same >= len(long_) - 2


def _covers(part: List[str], whole: List[str]) -> bool:
    return bool(part) and all(any(_form(p, w) for w in whole) for p in part)


def _named(name: str, entry: str) -> bool:
    """The ban names this person or tag: all of the ban's name words are in it (forbid «Петя» → «Петя Иванов»),
    or all of its words are in the ban (forbid «Петю не брать» → «Петя»)."""
    mine = _words(name)
    said = [w for w in _words(entry) if w not in _BAN_WORDS]
    return _covers(said, mine) or _covers(mine, said)


def blocked(row: dict, forbidden: Iterable[str]) -> bool:
    """A row whose person, tag or file is named in the never list (any word form of a name)."""
    names = list(row.get("who") or []) + list(row.get("tags") or [])
    for entry in forbidden:
        if str(entry).strip().casefold() == str(row.get("f", "")).casefold():
            return True
        if any(_named(name, str(entry)) for name in names):
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
