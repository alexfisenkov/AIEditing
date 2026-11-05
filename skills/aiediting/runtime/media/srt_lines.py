"""Where a subtitle breaks: by punctuation, evenly; never inside a name or after a preposition.

A run of words between hard breaks (a sentence end, a pause) is split by dynamic programming: every cue
fits MAX_CHARS (counted after the glossary's replacements) and MAX_SECONDS; a break after a comma costs
nothing, before «и/что/потому…» a little, inside a phrase more, after a possessive before its noun and
after a preposition much more, and inside a name, a glossary phrase or a compound conjunction (srt_words)
only when nothing else fits.
Line lengths are kept even, and a lone word on screen is avoided.
"""
from __future__ import annotations

import re
from typing import Callable, Dict, Iterable, List, Set

from .srt_words import CLINGS, OPENS, POSSESSIVES, bare, glued, sentence_end

MAX_CHARS = 42      # one comfortable subtitle line
MAX_SECONDS = 5.0
BREAK_GAP = 0.8     # a pause this long starts a new subtitle
FLASH = 0.5         # seconds: a part of a sentence shown this briefly cannot be read
NEVER = 100.0
_SOFT = re.compile(r"[,;:—–)»]$")


def glosser(glossary: Dict[str, str]) -> Callable[[str], str]:
    """The text as the glossary will make it (the same rule as srt._apply), to measure a line by."""
    rules = [(re.compile(r"(?<!\w){}(?!\w)".format(re.escape(k)), re.IGNORECASE), v)
             for k, v in sorted((glossary or {}).items(), key=lambda kv: -len(kv[0].split())) if k]

    def apply(text: str) -> str:
        for pattern, right in rules:
            text = pattern.sub(lambda _m: right, text)
        return text
    return apply


def _break_cost(run: List[dict], i: int, keep: Set[int]) -> float:
    """What it costs to end a cue after word i (the next cue starts with word i+1)."""
    here, after = run[i]["text"], bare(run[i + 1]["text"])
    if i in keep:
        return NEVER
    if _SOFT.search(here):
        return 0.0
    if bare(here) in CLINGS:
        return 8.0
    if after in OPENS:
        return 1.0
    return 6.0 if bare(here) in POSSESSIVES and after not in CLINGS else 3.0


def _text(tokens: Iterable[dict]) -> str:
    return " ".join(t["text"] for t in tokens)


def _split(run: List[dict], keep: Set[int], measure: Callable[[str], int]) -> List[List[dict]]:
    """Best cut of one run into cues; `keep` holds indexes inside the run that must not break."""
    n, best, back = len(run), [0.0] + [float("inf")] * len(run), [0] * (len(run) + 1)
    for b in range(1, n + 1):
        for a in range(b - 1, -1, -1):
            size = measure(_text(run[a:b]))
            if b - a > 1 and (size > MAX_CHARS or run[b - 1]["end"] - run[a]["start"] > MAX_SECONDS):
                break
            cost = best[a] + 1.0 + 2.0 * ((MAX_CHARS - min(size, MAX_CHARS)) / MAX_CHARS) ** 2
            cost += 4.0 if b - a == 1 and n > 1 else 0.0  # a lone word on screen
            cost += 4.0 if b - a < n and run[b - 1]["end"] - run[a]["start"] < FLASH else 0.0
            cost += _break_cost(run, b - 1, keep) if b < n else 0.0
            if cost < best[b]:
                best[b], back[b] = cost, a
    cuts, b = [], n
    while b > 0:
        cuts.append(run[back[b]:b])
        b = back[b]
    return cuts[::-1]


def runs(tokens: List[dict]) -> List[List[int]]:
    """Index ranges [start, end) between hard breaks: a sentence end or a pause."""
    out, start = [], 0
    for i in range(1, len(tokens) + 1):
        if i == len(tokens) or sentence_end(tokens[i - 1]["text"]) or \
                tokens[i]["start"] - tokens[i - 1]["end"] > BREAK_GAP:
            out.append([start, i])
            start = i
    return out


def lines(tokens: List[dict], glossary: Dict[str, str] = None) -> List[dict]:
    """tokens [{text, start, end}] (punctuation already on its word) → cues [{text, start, end}]."""
    keep = glued([t["text"] for t in tokens], glossary or {})
    gloss = glosser(glossary or {})
    measure = lambda text: len(gloss(text))  # noqa: E731
    cues = []
    for a, b in runs(tokens):
        for part in _split(tokens[a:b], {g - a for g in keep if a <= g < b}, measure):
            cues.append({"start": float(part[0]["start"]), "end": float(part[-1]["end"]), "text": _text(part)})
    return cues
