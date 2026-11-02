"""`params.speed`: how much faster the finished video plays (1.05 — on 5%), and what that does to its times."""
from __future__ import annotations

from typing import Dict, List

from .errors import PipelineError

SLOWEST, FASTEST = 0.5, 2.0  # beyond this a lesson is no longer watchable; a typo, not a wish


def rate_of(raw) -> float:
    """`params.speed` as a number, checked; 1.0 means «as it was»."""
    try:
        rate = float(raw)
    except (TypeError, ValueError):
        raise PipelineError("params.speed должен быть числом, например 1.05; сейчас: {}".format(raw))
    if not SLOWEST <= rate <= FASTEST:
        raise PipelineError("params.speed — от {} до {}; сейчас: {}".format(SLOWEST, FASTEST, raw))
    return rate


def scaled_words(words: List[Dict], rate: float) -> List[Dict]:
    """Words at their times in the sped-up video."""
    if rate == 1.0:
        return list(words)
    return [dict(w, start=w["start"] / rate, end=w["end"] / rate) for w in words]


def scale_rows(rows: List[Dict], rate: float, *keys: str) -> List[Dict]:
    """Report rows whose `keys` are times of the finished video, before the speed-up."""
    return [dict(r, **{k: r[k] / rate for k in keys if k in r}) for r in rows]
