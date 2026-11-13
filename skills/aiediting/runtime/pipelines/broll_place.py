"""Where an insert may stand: 3–6 s long, each edge on a cut or three seconds clear of one, never a long run of them."""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

MIN_LEN, MAX_LEN = 3.0, 6.0
ON_CUT = 0.15     # an edge this close to a cut counts as on it
SPARE = 3.0       # otherwise it keeps this far from every cut
SNAP = 1.0        # a start this close before a cut is moved onto it
RUN_GAP = 2.0     # less than this of the speaker between two inserts and they are one run
MAX_RUN = 3


def seams(keep: Sequence[Tuple[float, float]]) -> List[float]:
    """Where the kept spans meet in the cut video (seconds of that video)."""
    out, passed = [], 0.0
    for a, b in list(keep)[:-1]:
        passed += b - a
        out.append(round(passed, 3))
    return out


def _edge_ok(t: float, marks: Sequence[float]) -> bool:
    near = min((abs(t - m) for m in marks), default=None)
    return near is None or near <= ON_CUT or near >= SPARE


def fit(start: float, want: float, most: float, marks: Sequence[float], total: float) -> Optional[Tuple[float, float]]:
    """(start, length) in seconds of the cut video, or None. `want` is the phrase length, `most` what the clip can give."""
    starts = [start]
    near = min(marks, key=lambda m: abs(m - start), default=None)
    if near is not None and abs(near - start) <= SNAP and near not in starts:
        starts.append(near)
    for s in starts:
        longest = min(MAX_LEN, most, total - s)
        lengths = [max(MIN_LEN, min(want, longest))] + [m - s for m in marks if MIN_LEN <= m - s <= longest] + [longest, 5.0, 4.0, 3.0]
        for n in (round(x, 3) for x in lengths):
            if MIN_LEN - 1e-6 <= n <= longest + 1e-6 and _edge_ok(s, marks) and _edge_ok(s + n, marks):
                return round(s, 3), max(MIN_LEN, n)
    return None


def limit_run(slots: List[Dict], most: int = MAX_RUN) -> List[Dict]:
    """Slots ({"at", "len"}, seconds of the cut video) without a run of more than `most` inserts that follow each other."""
    kept: List[Dict] = []
    run = 0
    for slot in sorted(slots, key=lambda s: s["at"]):
        gap = slot["at"] - (kept[-1]["at"] + kept[-1]["len"]) if kept else RUN_GAP
        run = run + 1 if gap < RUN_GAP else 1
        if run > most:
            run -= 1  # dropped: the run stays as long as it was, and the next one is measured from the last kept
            continue
        kept.append(slot)
    return kept


def piece_of(row: Dict) -> Optional[Tuple[float, float]]:
    """(from, longest length) of a file's best stretch an insert can be cut from, or None if it gives under three seconds."""
    if row.get("type") == "фото":
        return 0.0, MAX_LEN
    dur = float(row.get("dur") or 0.0)
    spans = [(float(a), min(float(b), dur)) for a, b in (row.get("best") or [])] or [(0.0, dur)]
    for a, b in spans:
        if b - a >= MIN_LEN:
            return round(a, 3), round(min(b - a, MAX_LEN), 3)
    return None
