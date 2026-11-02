"""Repeated takes: a phrase that the next phrases start over is an earlier take; the last one stays.

An aside between the takes («нет, не так») goes with the earlier take, real speech between them never does. `slips`
adds the rest of what a person cuts by ear: a phrase restarted from its tail, an aside, a word left hanging.
"""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Dict, List, Sequence

from .slips import find_slips, is_aside
from .words import norm, phrases, quote

LOOK_AHEAD = 3      # phrases
MAX_GAP = 30.0      # seconds between an earlier take and the one that replaces it
SIMILAR = 0.75
BRIDGE_WORDS = 3    # a phrase this short between two takes is not content
MARGIN = 0.05       # seconds left before the take that stays


def _same_start(a: List[str], b: List[str]) -> bool:
    if not a or not b:
        return False
    k = min(len(a), 3)
    if len(a) <= len(b) and a[:k] == b[:k]:
        return True
    return len(a) >= 3 and SequenceMatcher(None, a, b[:len(a)]).ratio() >= SIMILAR


def _take(i: int, j: int, ph: List[Dict], keys: List[List[str]]) -> Dict:
    """Phrase i with the asides before phrase j, which starts it over; up to j when nothing else is between them."""
    last = i
    while last + 1 < j and (len(keys[last + 1]) <= BRIDGE_WORDS or is_aside(keys[last + 1])):
        last += 1
    end = max(ph[last]["end"], ph[j]["start"] - MARGIN) if last == j - 1 else ph[last]["end"]
    return {"drop": [ph[i]["start"], end], "keep": [ph[j]["start"], ph[j]["end"]],
            "said": quote([w for p in ph[i:last + 1] for w in p["words"]], 40), "kept": quote(ph[j]["words"])}


def _broken_off(ph: List[Dict]) -> List[Dict]:
    """Phrases cut further where a word breaks off: what follows «слово--» starts anew even without a pause."""
    out: List[Dict] = []
    for p in ph:
        cur: List[Dict] = []
        for w in p["words"]:
            cur.append(w)
            if str(w["text"]).rstrip().endswith("--"):
                out.append({"start": cur[0]["start"], "end": w["end"], "words": cur})
                cur = []
        if cur:
            out.append({"start": cur[0]["start"], "end": cur[-1]["end"], "words": cur})
    return out


def find_retakes(words: Sequence[Dict]) -> List[Dict]:
    """[{id, drop:[a,b], keep:[a,b], said, kept}] — every earlier take with the take that replaces it."""
    ph = _broken_off(phrases([w for w in words if w.get("type") != "filler"]))
    keys = [[norm(w["text"]) for w in p["words"] if norm(w["text"])] for p in ph]
    found: List[Dict] = []
    for i, p in enumerate(ph):
        for j in range(i + 1, min(i + 1 + LOOK_AHEAD, len(ph))):
            if ph[j]["start"] - p["end"] > MAX_GAP:
                break
            if _same_start(keys[i], keys[j]):
                found.append(_take(i, j, ph, keys))
                break
    found = sorted(found + find_slips(ph, keys, found), key=lambda t: t["drop"][0])
    return [dict(t, id="r{}".format(k + 1)) for k, t in enumerate(found)]


def plan_retakes(ctx, words: Sequence[Dict]) -> List[Dict]:
    """Earlier takes the person agreed to drop (nothing without their «да»); an answer may name them by id."""
    items = find_retakes(words)
    if not items:
        return []
    ok, data = ctx.ask("retakes", "Похоже на повторы и оговорки: вырезать их, оставив последний дубль? "
                       "Уберите из items то, что вырезать не надо.", {"items": items})
    if not ok:
        return []
    by_id = {t["id"]: t for t in items}
    return [by_id[it] if isinstance(it, str) and it in by_id else it for it in data.get("items", []) if isinstance(it, dict) or it in by_id]
