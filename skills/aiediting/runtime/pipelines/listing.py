"""A list as it is said: pieces between commas (or after a colon), the last one split at «и»."""
from __future__ import annotations

from typing import Dict, List, Sequence

AND = ("и", "а", "или", "and", "or")
ITEM_WORDS, MAX_ITEMS = 4, 6


def clean(text: str) -> str:
    return str(text).strip().strip(".,;:!?…«»\"'()—")


def chunks(words: Sequence[Dict]):
    """(lead, pieces): words up to a colon, then pieces between commas — lists are said with commas."""
    lead, out, cur = [], [], []
    for w in words:
        raw, word = str(w["text"]).strip(), clean(w["text"])
        if word:
            cur.append(word)
        if raw.endswith(":") and not out:
            lead, cur = lead + cur, []
        elif raw.endswith((",", ";")):
            out.append(cur)
            cur = []
    return lead, out + ([cur] if cur else [])


def split_and(chunk: List[str]) -> List[List[str]]:
    """«spec и plan» → spec, plan: the last point of a list often comes with «и»."""
    parts: List[List[str]] = [[]]
    for w in chunk:
        if w.lower() in AND:
            parts.append([])
        else:
            parts[-1].append(w)
    return [p for p in parts if p]


def items(pieces: List[List[str]], trigger) -> List[str]:
    """The points: the first piece loses its lead-in («файлы agents.md» → agents.md)."""
    first, rest = pieces[0], pieces[1:-1] + split_and(pieces[-1])
    hit = max((k for k, w in enumerate(first) if trigger.match(w)), default=-1) if trigger else -1
    if hit >= 0:
        first = first[hit + 1:]
    else:
        first = first[-max(1, min((len(c) for c in rest), default=1)):]
    return [" ".join(p[:ITEM_WORDS]) for p in [first] + rest if p][:MAX_ITEMS]
