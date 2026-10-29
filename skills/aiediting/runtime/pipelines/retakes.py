"""Repeated takes: a phrase that the next phrases start over is an earlier take; the last one stays."""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Dict, List, Sequence

from .words import norm, phrases, quote

LOOK_AHEAD = 3      # phrases
MAX_GAP = 30.0      # seconds between an earlier take and the one that replaces it
SIMILAR = 0.75


def _same_start(a: List[str], b: List[str]) -> bool:
    if not a or not b:
        return False
    k = min(len(a), 3)
    if len(a) <= len(b) and a[:k] == b[:k]:
        return True
    return len(a) >= 3 and SequenceMatcher(None, a, b[:len(a)]).ratio() >= SIMILAR


def find_retakes(words: Sequence[Dict]) -> List[Dict]:
    """[{id, drop:[a,b], keep:[a,b], said, kept}] — every earlier take with the take that replaces it."""
    plain = [w for w in words if w.get("type") != "filler"]
    ph = phrases(plain)
    keys = [[norm(w["text"]) for w in p["words"] if norm(w["text"])] for p in ph]
    found = []
    for i, p in enumerate(ph):
        for j in range(i + 1, min(i + 1 + LOOK_AHEAD, len(ph))):
            if ph[j]["start"] - p["end"] > MAX_GAP:
                break
            if _same_start(keys[i], keys[j]):
                found.append({"id": "r{}".format(len(found) + 1), "drop": [p["start"], p["end"]],
                              "keep": [ph[j]["start"], ph[j]["end"]], "said": quote(p["words"]),
                              "kept": quote(ph[j]["words"])})
                break
    return found


def plan_retakes(ctx, words: Sequence[Dict]) -> List[Dict]:
    """Earlier takes the person agreed to drop (nothing without their «да»)."""
    items = find_retakes(words)
    if not items:
        return []
    ok, data = ctx.ask("retakes", "Похоже на повторы: вырезать ранние дубли и оставить последний? "
                       "Уберите из items то, что вырезать не надо.", {"items": items})
    return [it for it in data.get("items", [])] if ok else []
