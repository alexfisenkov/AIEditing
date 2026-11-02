"""Recognised word times checked against the sound, for formats cut by loudness.

A word lives by its middle (`kept.alive`). A recogniser sometimes stretches a word across the pause next to it,
or places a phrase tail inside a later silence: the sound of such a word stays in the video, the word falls out
of the subtitles. Only what can belong nowhere else moves; a hesitation never does, because its times are what
gets cut. The times in the cached transcript stay as recognised.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .kept import alive
from .report import stamp
from .timeline import Span
from .words import quote

LONGEST = 2.5    # no spoken word lasts longer unless sound runs through all of it
MIN_WORD = 0.25  # free sound shorter than this per word is a tail of the last word or a breath
CLICK = 0.1      # sound this short is a click, whatever margin the cut has added to it
BREATH = 0.7     # a silence this short inside a phrase does not end it
_ENDS = (".", "!", "?", "…")


def _overlaps(a: float, b: float, loud: Sequence[Span]) -> List[Span]:
    return [(max(a, x), min(b, y)) for x, y in loud if x < b and a < y]


def _unstretched(w: Dict, parts: List[Span], loud: Sequence[Span]) -> Optional[Span]:
    """A word longer than LONGEST: cut back to its sound if a pause is inside it, else left as it is."""
    if alive(w["end"], loud) and not alive(w["start"], loud):
        a, b = parts[-1]
        return max(a, b - LONGEST), b
    a, b = parts[0]
    return (a, min(b, a + LONGEST)) if b < w["end"] else None


def _fitted(w: Dict, loud: Sequence[Span]) -> Optional[Span]:
    """New times of a word that touches sound but does not sit in it; None when it needs no change."""
    parts = _overlaps(w["start"], w["end"], loud)
    if not parts:
        return None
    if w["end"] - w["start"] > LONGEST:
        return _unstretched(w, parts, loud)
    if alive((w["start"] + w["end"]) / 2.0, loud):
        return None
    return max(parts, key=lambda p: p[1] - p[0])


def _free_sound(words: List[Dict], i: int, j: int, loud: Sequence[Span], pad: float) -> Optional[Span]:
    """Sound right after the word before the run, if that word left its sentence open; no longer than the run."""
    if i == 0 or str(words[i - 1]["text"]).strip().endswith(_ENDS):
        return None
    after, count = words[i - 1]["end"], j - i
    for a, b in _speech_runs(loud):
        if a <= after < b:
            end = min(b - pad, words[i]["start"], after + words[j - 1]["end"] - words[i]["start"])
            return (after, end) if end - after >= MIN_WORD * count else None
    return None


def _speech_runs(loud: Sequence[Span]) -> List[Span]:
    """Loud stretches with the short breaths between them closed: a dense cut splits speech at each."""
    runs: List[Span] = []
    for a, b in loud:
        if runs and a - runs[-1][1] <= BREATH:
            runs[-1] = (runs[-1][0], b)
        else:
            runs.append((a, b))
    return runs


def _spread(words: List[Dict], span: Span) -> None:
    """Lays the words over `span` in order, each by its length in letters."""
    sizes = [max(1, len(str(w["text"]).strip())) for w in words]
    at, unit = span[0], (span[1] - span[0]) / float(sum(sizes))
    for w, size in zip(words, sizes):
        w["start"], w["end"] = round(at, 3), round(at + size * unit, 3)
        at += size * unit


def _orphan(w: Dict, loud: Sequence[Span]) -> bool:
    return not _overlaps(w["start"], w["end"], loud) and not alive((w["start"] + w["end"]) / 2.0, loud)


def _orphan_runs(words: List[Dict], loud: Sequence[Span], fixed: Callable[[Dict], bool]) -> List[Tuple[int, int]]:
    """Index ranges [i, j) of neighbouring words with no sound under any of them."""
    runs, i = [], 0
    while i < len(words):
        j = i
        while j < len(words) and not fixed(words[j]) and _orphan(words[j], loud):
            j += 1
        if j > i:
            runs.append((i, j))
        i = max(j, i + 1)
    return runs


def repaired(transcript: Dict, loud: Sequence[Span], pad: float = 0.12,
             fixed: Callable[[Dict], bool] = lambda w: False) -> Tuple[Dict, List[str]]:
    """(a copy of the transcript with corrected times, what moved and from where) by the loud stretches.

    `pad` is the margin `speech_spans` added around the sound; a word `fixed` says about keeps its times."""
    all_words = [dict(w) for w in (transcript or {}).get("words", [])]
    words = [w for w in all_words if w.get("type") != "spacing" and str(w.get("text", "")).strip()]
    sound = [s for s in loud if s[1] - s[0] >= 2 * pad + CLICK]
    moved: List[str] = []
    for w in words:
        fitted = None if fixed(w) else _fitted(w, sound)
        if fitted:
            moved.append("{} {}–{} → {}".format(quote([w]), stamp(w["start"]), stamp(w["end"]), stamp(fitted[0])))
            w["start"], w["end"] = round(fitted[0], 3), round(fitted[1], 3)
    for i, j in _orphan_runs(words, sound, fixed):
        span = _free_sound(words, i, j, sound, pad)
        if span:
            moved.append("{} {} → {}".format(quote(words[i:j]), stamp(words[i]["start"]), stamp(span[0])))
            _spread(words[i:j], span)
    return dict(transcript or {}, words=all_words), moved
