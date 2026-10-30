"""Continuous speech: with `word_gap` in the profile only the stretches where words are said stay.

Loudness alone keeps breaths, clicks and room noise that rise above the threshold, and the stretch between
a dropped take and the next one. Here a stretch with no word longer than `word_gap` s is cut whatever its
loudness. Each word is widened by `word_lead` / `word_tail` s for its first and last sounds; the widening
is trimmed to where there is sound (the loudness spans), and a word itself is never cut into.
"""
from __future__ import annotations

from typing import Dict, List, Sequence

from .timeline import Span, intersect, merge

LEAD, TAIL = 0.08, 0.12  # s: room for a word's first and last sounds that the recogniser's timing misses


def word_runs(words: Sequence[Dict], lead: float, tail: float, join: float) -> List[Span]:
    """Words widened by lead/tail; a pause of at most `join` s between two words stays inside one run."""
    runs: List[Span] = []
    last = None
    for w in sorted(words, key=lambda w: (float(w["start"]), float(w["end"]))):
        a, b = float(w["start"]), float(w["end"])
        if runs and a - last <= join:
            runs[-1] = (runs[-1][0], max(runs[-1][1], b + tail))
        else:
            runs.append((max(0.0, a - lead), b + tail))
        last = b if last is None else max(last, b)
    return merge(runs)


def by_words(loud: Sequence[Span], words: Sequence[Dict], join: float, total: float,
             lead: float = LEAD, tail: float = TAIL) -> List[Span]:
    """Kept spans: the word runs where there is sound, plus every word whole; no words — `loud` as is."""
    if not words:
        return list(loud)
    heard = [s for a, b in word_runs(words, lead, tail, join) for s in intersect(loud, a, b)]
    whole = [(max(0.0, float(w["start"])), min(total, float(w["end"]))) for w in words]
    return [(round(a, 3), round(min(b, total), 3)) for a, b in merge(heard + whole) if min(b, total) > a]


def plan_words(ctx, loud: List[Span]) -> List[Span]:
    """`loud` narrowed to the words when the profile asks for continuous speech (`word_gap`)."""
    if ctx.p("word_gap") is None or not loud:
        return loud
    from .words import spoken

    return by_words(loud, spoken(ctx.transcript()), float(ctx.p("word_gap")), float(ctx.info["duration"]),
                    lead=float(ctx.p("word_lead", LEAD)), tail=float(ctx.p("word_tail", TAIL)))
