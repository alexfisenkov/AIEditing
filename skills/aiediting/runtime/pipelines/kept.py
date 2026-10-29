"""What the cut leaves of the speech: a word lives if its middle is in a kept span.

A moment on the edge belongs to the stretch that follows it: a word of zero length at the very start
of a cut take (Scribe gives some) is not left behind in the kept span that ends there.
"""
from __future__ import annotations

from typing import Dict, List, Sequence

from .timeline import Span


def alive(t: float, keep: Sequence[Span]) -> bool:
    """True if source moment `t` is inside a kept span (a span owns its start, not its end)."""
    return any(a <= t < b for a, b in keep)


def kept_words(words: Sequence[Dict], keep: Sequence[Span]) -> List[Dict]:
    """The words whose middle survived the cut, still in source time."""
    return [w for w in words if alive((w["start"] + w["end"]) / 2.0, keep)]


def kept_phrases(ctx) -> List[Dict]:
    """Phrases of what is still said after the cuts (source time): places for cards and inserts."""
    from .words import phrases, spoken

    return phrases(kept_words(spoken(ctx.transcript()), ctx.keep))
