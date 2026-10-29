"""A list as it is said: pieces between commas (or after a colon), the last one split at «и»."""
from __future__ import annotations

import re
from typing import Dict, List, Sequence

from .filenames import EXT
from .points import ITEM_WORDS, MAX_ITEMS, clean, content, split_and


def chunks(words: Sequence[Dict]):
    """(lead, pieces): words up to a colon, then pieces between commas — lists are said with commas.

    A file said as two words («agents MD») becomes one («agents.md»)."""
    lead, out, cur, joined = [], [], [], False
    for w in words:
        raw, word = str(w["text"]).strip(), clean(w["text"])
        if word.lower() in EXT and cur and joined and "." not in cur[-1]:
            cur[-1] = "{}.{}".format(cur[-1], word.lower())
        elif word:
            cur.append(word)
        joined = bool(word) and not re.search(r"[.,;:!?…]$", raw)
        if raw.endswith(":") and not out:
            lead, cur = lead + cur, []
        elif raw.endswith((",", ";")):
            out.append(cur)
            cur = []
    return lead, out + ([cur] if cur else [])


def _parts(pieces: List[List[str]], trigger) -> List[List[str]]:
    """The pieces as points; the first loses its lead-in («файлы agents.md» → agents.md)."""
    first, rest = pieces[0], pieces[1:-1] + split_and(pieces[-1])
    hit = max((k for k, w in enumerate(first) if trigger.match(w)), default=-1) if trigger else -1
    first = first[hit + 1:] if hit >= 0 else first[-max(1, min((len(c) for c in rest), default=1)):]
    return [first] + rest


def items(pieces: List[List[str]], trigger) -> List[str]:
    """Meaningful points, filler-only pieces dropped (steps: «открыть терминал, вставить команду…»)."""
    kept = [content(p) if len(p) <= ITEM_WORDS else p for p in _parts(pieces, trigger)]  # long = a clause
    return [" ".join(p[:ITEM_WORDS]) for p in kept if p][:MAX_ITEMS]


def listed(pieces: List[List[str]]) -> List[str]:
    """Points of a real list, or []: at least three short ones (up to three words as said), most points
    short, and at most one filler-only piece between them («я, например, да, там, …» is talk, not a list)."""
    points, gaps, pending = [], 0, 0
    for part in _parts(pieces, None):
        words = content(part)
        if not words:
            pending += 1
            continue
        gaps, pending = gaps + (pending if points else 0), 0
        points.append((len(part), " ".join(words[:ITEM_WORDS])))
    few = [t for n, t in points if n <= 3]
    ok = len(few) >= 3 and len(few) * 3 >= len(points) * 2 and gaps <= 1
    return few[:MAX_ITEMS] if ok else []
