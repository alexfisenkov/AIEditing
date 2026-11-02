"""What a cut inside speech does to the words around it: the sound of the cut word goes whole, the text stays correct.

A recogniser places a word's start after its first consonant: cut at that time, «с» of «соответственно» stays in the
video. So a cut starts right after the word before it. A word cut with its commas leaves the comma before it hanging
(«вот можно, здесь»), a sentence cut to its end leaves the last kept word without a full stop.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from .wordcut import LEAD, TAIL
from .words import norm

AIR = 0.01   # left after the word before the cut
_ENDS = (".", "!", "?", "…")
OPENS_A_CLAUSE = {"то", "что", "чтобы", "который", "которая", "которое", "которые", "которых", "которой", "потому",
                  "но", "а", "если", "когда", "где", "как", "либо", "или"}


def _before(words: Sequence[Dict], t: float) -> Optional[Dict]:
    found = None
    for w in words:
        if w["end"] > t:
            break
        found = w
    return found


def widened(words: Sequence[Dict], takes: Sequence[Dict]) -> List[Dict]:
    """`takes` with each start moved back to just after the word before it, at most LEAD."""
    out = []
    for t in takes:
        a, b = t["drop"]
        prev = _before(words, a)
        start = max(prev["end"] + AIR, a - LEAD) if prev else a - LEAD
        out.append(dict(t, drop=[round(min(a, max(0.0, start)), 3), b]))
    return out


def wordless_inside(keep: Sequence, words: Sequence[Dict], gap: float, longest: float) -> List:
    """Stretches of kept speech with no word for `gap` s: a grunt, a breath, sound above the loudness threshold.

    Each word keeps its margins (LEAD before, TAIL after); a stretch over `longest` s may be a demo and stays."""
    out = []
    for a, b in keep:
        at, first = a, True
        for w in [w for w in words if w["start"] < b and a < w["end"]] + [None]:
            until = w["start"] if w else b
            if until - at >= gap and until - at <= longest:
                x, y = at + (0.0 if first else TAIL), until - (LEAD if w else 0.0)
                if y > x:
                    out.append((round(x, 3), round(y, 3)))
            if w:
                at, first = max(at, w["end"]), False
    return out


def _inside(w: Dict, drops: Sequence) -> bool:
    return any(a <= (w["start"] + w["end"]) / 2.0 < b for a, b in drops)


def tidy(words: Sequence[Dict], takes: Sequence[Dict]) -> None:
    """Fixes the punctuation of the words next to each cut, in place; the cached transcript is not touched."""
    drops = sorted(tuple(t["drop"]) for t in takes)
    for a, b in drops:
        gone = [w for w in words if a <= (w["start"] + w["end"]) / 2.0 < b]
        if not gone or not norm(gone[-1]["text"]):
            continue
        kept = [w for w in words if not _inside(w, drops) and norm(w["text"])]
        prev = next((w for w in reversed(kept) if w["end"] <= gone[0]["start"] + 0.001), None)
        after = next((w for w in kept if w["start"] >= gone[-1]["end"] - 0.001), None)
        if prev is None:
            continue
        left, last = str(prev["text"]).rstrip(), str(gone[-1]["text"]).rstrip()
        if last.endswith(_ENDS):
            if not left.endswith(_ENDS):
                prev["text"] = left.rstrip(",") + last[-1]
        elif left.endswith(",") and last.endswith(",") and (after is None or norm(after["text"]) not in OPENS_A_CLAUSE):
            prev["text"] = left[:-1]
