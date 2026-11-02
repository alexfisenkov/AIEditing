"""Slips a person cuts by ear besides whole retakes; each is only a proposal, the person decides.

A phrase restarted from its own tail («и хотите их, и хотите их адаптировать»), a short aside to oneself
(«нет, без этого», «вот это уже больше не надо»), a word left hanging before a pause («…Claude Code и,»).
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence

from .words import norm, quote

MIN_RESTART = 2     # words: one repeated word is often emphasis («все, все, все»)
MAX_RESTART = 8
RESTART_GAP = 3.0   # seconds between the tail and its restart
HANGING_PAUSE = 0.7
HANGING = {"и", "а", "но", "соответственно", "ну", "вот", "то", "что", "как", "в", "на", "с"}
CORRECTIONS = (("перепишу",), ("без", "этого"), ("не", "так"), ("сначала", "скажу"), ("диктую",))
CORRECTION_WORDS = 4  # longer, it is ordinary speech («Если что-то пошло не так, напишите мне»), unless it opens with «нет»
ALWAYS = (("уже", "больше", "не", "надо"),)
SHORT = (("еще", "раз"), ("не-не",))
ASIDE_WORDS, SHORT_WORDS = 16, 5
FALSE_START_WORDS = 3  # «Это видео--»: a phrase this short that breaks off
_ENDS = (".", "!", "?", "…")


def _has(keys: Sequence[str], cue: Sequence[str]) -> bool:
    return any(list(keys[i:i + len(cue)]) == list(cue) for i in range(len(keys) - len(cue) + 1))


def is_aside(keys: Sequence[str]) -> bool:
    if len(keys) > ASIDE_WORDS:
        return False
    if any(_has(keys, c) for c in ALWAYS) or (len(keys) <= SHORT_WORDS and any(_has(keys, c) for c in SHORT)):
        return True
    opens_with_no = keys[:1] == ["нет"] or keys[:2] == ["так", "нет"]
    return (len(keys) <= CORRECTION_WORDS or opens_with_no) and any(_has(keys, c) for c in CORRECTIONS)


def _is_false_start(keys: Sequence[str], words: Sequence[Dict]) -> bool:
    return bool(words) and len(keys) <= FALSE_START_WORDS and str(words[-1]["text"]).rstrip().endswith("--")


def _tail_restart(a: Sequence[str], b: Sequence[str]) -> int:
    """How many last words of `a` the phrase `b` starts with (the longest such run), 0 if too few."""
    for n in range(min(len(a), len(b), MAX_RESTART), MIN_RESTART - 1, -1):
        if list(a[-n:]) == list(b[:n]):
            return n
    return 0


def _inner_restart(keys: Sequence[str], words: Sequence[Dict]) -> Optional[tuple]:
    """(start, length) of words said twice in a row inside one phrase; emphasis and a repeated name do not count."""
    for n in range(MAX_RESTART, MIN_RESTART - 1, -1):
        for s in range(len(keys) - 2 * n + 1):
            run = keys[s:s + n]
            if list(run) == list(keys[s + n:s + 2 * n]) and len(set(run)) > 1 and \
                    not any(re.search("[A-Za-z]", str(w["text"])) for w in words[s:s + n]):
                return s, n
    return None


def _item(words: List[Dict], next_phrase: Dict, why: str, before: str = "") -> Dict:
    item = {"drop": [words[0]["start"], words[-1]["end"]], "keep": [next_phrase["start"], next_phrase["end"]],
            "said": quote(words, 40), "kept": quote(next_phrase["words"]), "why": why}
    return dict(item, before=before) if before else item


def _aside(i: int, ph: List[Dict], after: Dict, free) -> Optional[Dict]:
    """An aside, with the phrase it broke off if it did: «контакт там бу-- а, не, вот это уже больше не надо»."""
    p, broke = ph[i], i > 0 and str(ph[i - 1]["words"][-1]["text"]).rstrip().endswith("--")
    words = (ph[i - 1]["words"] if broke else []) + p["words"]
    if not free(words[0]["start"], p["end"]):
        return None
    start = i - 1 if broke else i
    return _item(words, after, "реплика в сторону", quote(ph[start - 1]["words"]) if start else "")


def _of_phrase(i: int, ph: List[Dict], keys: List[List[str]], free) -> List[Dict]:
    """The slips of phrase i."""
    p, after = ph[i], ph[i + 1] if i + 1 < len(ph) else None
    spoken = [w for w in p["words"] if norm(w["text"])]
    if not spoken or len(spoken) != len(keys[i]):
        return []
    if after and is_aside(keys[i]):
        return [s for s in [_aside(i, ph, after, free)] if s]
    if after and _is_false_start(keys[i], spoken):
        return [_item(p["words"], after, "начал и бросил")] if free(p["start"], p["end"]) else []
    found: List[Dict] = []
    inner = _inner_restart(keys[i], spoken)
    if inner and free(spoken[inner[0]]["start"], spoken[inner[0] + inner[1] - 1]["end"]):
        found.append(_item(spoken[inner[0]:inner[0] + inner[1]], after or p, "фраза начата заново"))
    last = str(spoken[-1]["text"]).rstrip()
    if not after or last.endswith(_ENDS):
        return found
    n = _tail_restart(keys[i], keys[i + 1]) if after["start"] - p["end"] <= RESTART_GAP else 0
    if n and free(spoken[-n]["start"], p["end"]):
        found.append(_item(spoken[-n:], after, "фраза начата заново"))
    elif len(keys[i]) > 1 and keys[i][-1] in HANGING and last.endswith(",") and \
            after["start"] - p["end"] >= HANGING_PAUSE and free(spoken[-1]["start"], p["end"]):
        found.append(_item(spoken[-1:], after, "слово повисло перед паузой"))
    return found


def find_slips(ph: List[Dict], keys: List[List[str]], takes: List[Dict]) -> List[Dict]:
    """Proposals over phrases `ph` with word keys `keys`; what a whole take in `takes` already drops is skipped."""
    def free(start: float, end: float) -> bool:
        return not any(start < t["drop"][1] and t["drop"][0] < end for t in takes)

    return [s for i in range(len(ph)) for s in _of_phrase(i, ph, keys, free)]
