"""Word times estimated from phrase times, for services that return only segments."""
from __future__ import annotations

from typing import Iterable, List


def words_from_segments(segments: Iterable[dict]) -> List[dict]:
    """Splits each segment's text into words and shares its time by word length."""
    words: List[dict] = []
    for seg in segments:
        tokens = str(seg.get("text", "")).split()
        try:
            start, end = float(seg["start"]), float(seg["end"])
        except (KeyError, TypeError, ValueError):
            continue
        total = sum(len(t) for t in tokens)
        if not tokens or total == 0 or end <= start:
            continue
        cursor = start
        for token in tokens:
            stop = cursor + (end - start) * len(token) / total
            words.append({"text": token, "start": cursor, "end": stop, "type": "word"})
            cursor = stop
    return words
