"""Where inserts may go: moments of speech, at most one per `every` seconds, never on a chapter plate."""
from __future__ import annotations

from typing import Dict, List, Optional

from .chapters import plate_windows
from .moments import find
from .words import phrases, spoken

EVERY, LOW, HIGH = 45.0, 30.0, 60.0


def settings(ctx) -> Dict:
    raw = ctx.p("animations")
    return dict(raw) if isinstance(raw, dict) else {}


def every(ctx) -> float:
    """`params.animations.every`, kept inside 30–60 s (45 when not set)."""
    return min(HIGH, max(LOW, float(settings(ctx).get("every", EVERY))))


def length(ctx, slot: Dict) -> float:
    """How long an insert stays: the profile's `seconds`, else by the number of points (4–8 s)."""
    fixed = settings(ctx).get("seconds")
    return float(fixed) if fixed else min(8.0, max(4.0, 3.0 + 0.6 * len(slot.get("items", []))))


def over(a: float, b: float, spans: List[Dict]) -> Optional[Dict]:
    """The first span of `spans` that [a, b) touches."""
    return next((w for w in spans if a < w["end"] and b > w["start"]), None)


def slots(ctx) -> List[Dict]:
    """[{start, end, template, title, items, said}] to put to the person."""
    plates, out = plate_windows(ctx), []
    for m in find(phrases(spoken(ctx.transcript()))):
        m["end"] = round(m["start"] + length(ctx, m), 3)
        if over(m["start"], m["end"], plates) or (out and m["start"] - out[-1]["start"] < every(ctx)):
            continue
        out.append(m)
    return out
