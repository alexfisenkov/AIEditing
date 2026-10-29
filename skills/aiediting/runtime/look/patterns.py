"""What looks secret in a piece of text: e-mail, phone, card number, API key, money."""
from __future__ import annotations

import re
from typing import Dict, List

_NUM = r"\d{1,3}(?:[   .,]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?"
_CUR_AFTER = r"₽|руб(?:лей|ля|ль)?\.?|р\.|\$|€|USD|EUR|RUB|долл(?:аров|ара|ар)?|евро"
_SCALE = r"(?:[  ]?(?:тыс\.?|млн\.?|млрд\.?|[кk]))?"

# Order is priority: when two hits overlap, the earlier kind wins.
PATTERNS = [
    ("key", re.compile(r"(?<![\w-])(?:sk-(?:proj-|ant-)?[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{30,}"
                       r"|github_pat_[A-Za-z0-9_]{30,}|xox[abpr]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}"
                       r"|AIza[0-9A-Za-z_-]{35})")),
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")),
    ("card", re.compile(r"(?<![\d+])\d(?:[ -]?\d){12,18}(?!\d)")),
    ("phone", re.compile(r"(?<![\w+])(?:\+\d{1,3}|8)[ -]?\(?\d{2,4}\)?(?:[ -]?\d){5,8}(?!\d)")),
    ("money", re.compile(r"(?:[$€₽][  ]?(?:{n}))|(?:(?:{n}){s}[  ]?(?:{c}))(?![\w])".format(
        n=_NUM, s=_SCALE, c=_CUR_AFTER), re.IGNORECASE)),
]


def luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch) * (2 if i % 2 else 1)
        total += d - 9 if d > 9 else d
    return total % 10 == 0


def _valid(kind: str, text: str) -> bool:
    digits = re.sub(r"\D", "", text)
    if kind == "card":
        return 13 <= len(digits) <= 19 and luhn_ok(digits)
    if kind == "phone":
        return 10 <= len(digits) <= 15
    return True


def scan_text(text: str) -> List[Dict]:
    """Hits as {"kind", "text", "start", "end"} (character offsets), in reading order, no overlaps."""
    hits: List[Dict] = []
    for kind, rx in PATTERNS:
        for m in rx.finditer(text or ""):
            if not _valid(kind, m.group(0)):
                continue
            if any(m.start() < h["end"] and h["start"] < m.end() for h in hits):
                continue
            hits.append({"kind": kind, "text": m.group(0), "start": m.start(), "end": m.end()})
    return sorted(hits, key=lambda h: h["start"])
