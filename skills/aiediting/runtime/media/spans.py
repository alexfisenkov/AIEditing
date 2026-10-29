"""Where the speech is: silencedetect, then speech runs with a safety margin around each."""
from __future__ import annotations

import re
from typing import List, Tuple

from .ffmpeg import ensure_file, run
from .probe import probe

Span = Tuple[float, float]
_START = re.compile(r"silence_start:\s*(-?[\d.]+)")
_END = re.compile(r"silence_end:\s*(-?[\d.]+)")


def _silences(media, gap: float, db: float) -> List[Span]:
    err = run(["-i", media, "-vn", "-af",
               "silencedetect=noise={}dB:d={}".format(db, gap), "-f", "null", "-"]).stderr
    found, start = [], None
    for line in err.splitlines():
        m = _START.search(line)
        if m:
            start = max(0.0, float(m.group(1)))
            continue
        m = _END.search(line)
        if m and start is not None:
            found.append((start, float(m.group(1))))
            start = None
    if start is not None:
        found.append((start, float("inf")))
    return found


def _merge(spans: List[Span]) -> List[Span]:
    merged: List[Span] = []
    for a, b in sorted(spans):
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        elif b > a:
            merged.append((a, b))
    return merged


def speech_spans(media, gap: float = 0.5, pad: float = 0.12, db: float = -30) -> List[Span]:
    """Speech runs: everything except silences of at least `gap` s, widened by `pad` s each side."""
    media = ensure_file(media)
    info = probe(media)
    if not info["has_audio"]:
        return [(0.0, info["duration"])] if info["duration"] > 0 else []
    total = min(info["duration"], info["audio_duration"] or info["duration"])
    speech, cursor = [], 0.0
    for a, b in _silences(media, gap, db):
        if a > cursor:
            speech.append((cursor, a))
        cursor = max(cursor, min(b, total))
    if cursor < total:
        speech.append((cursor, total))
    padded = [(max(0.0, a - pad), min(total, b + pad)) for a, b in speech]
    return [(round(a, 3), round(b, 3)) for a, b in _merge(padded)]
