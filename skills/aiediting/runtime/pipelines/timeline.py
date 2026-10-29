"""Span arithmetic in seconds: what is kept, what is cut, where a source moment lands after the cut."""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

Span = Tuple[float, float]


def merge(spans: Sequence[Span]) -> List[Span]:
    out: List[Span] = []
    for a, b in sorted((float(a), float(b)) for a, b in spans if float(b) > float(a)):
        if out and a <= out[-1][1] + 1e-6:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def subtract(keep: Sequence[Span], cuts: Sequence[Span]) -> List[Span]:
    result = merge(keep)
    for c0, c1 in merge(cuts):
        nxt: List[Span] = []
        for a, b in result:
            if c1 <= a or c0 >= b:
                nxt.append((a, b))
                continue
            if c0 > a:
                nxt.append((a, c0))
            if c1 < b:
                nxt.append((c1, b))
        result = nxt
    return result


def intersect(keep: Sequence[Span], a: float, b: float) -> List[Span]:
    return [(max(x, a), min(y, b)) for x, y in merge(keep) if min(y, b) > max(x, a)]


def removed(keep: Sequence[Span], total: float) -> List[Span]:
    """The pieces between kept spans (what the cut throws away)."""
    return subtract([(0.0, total)], keep)


def length(spans: Sequence[Span]) -> float:
    return sum(b - a for a, b in spans)


def to_out(t: float, keep: Sequence[Span]) -> Optional[float]:
    """Where source moment `t` lands in the cut video; None if it was cut away."""
    passed = 0.0
    for a, b in keep:
        if a <= t <= b:
            return round(passed + t - a, 3)
        passed += b - a
    return None


def map_range(a: float, b: float, keep: Sequence[Span]) -> Optional[Span]:
    """Source range -> output range (cuts inside it simply shorten it); None if all of it is cut."""
    inside = intersect(keep, a, b)
    if not inside:
        return None
    return to_out(inside[0][0], keep), to_out(inside[-1][1], keep)
