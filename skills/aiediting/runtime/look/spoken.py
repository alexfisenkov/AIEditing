"""Secret-looking text in the transcript: hits mapped back to word times and the nearest snapshot."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from .frames import frame_time
from .patterns import scan_text


def _spoken(transcript: Optional[Dict]):
    """Transcript as one string plus (start_char, end_char, word) for every word."""
    text, spans = "", []
    for w in (transcript or {}).get("words", []):
        if w.get("type") == "spacing":
            text += w.get("text") or " "
            continue
        if text and not text.endswith(" "):
            text += " "
        spans.append((len(text), len(text) + len(w["text"]), w))
        text += w["text"]
    return text, spans


def _nearest(frames: List[Path], t: float) -> Optional[Path]:
    timed = [(abs(frame_time(f) - t), f) for f in frames if frame_time(f) is not None]
    return min(timed, key=lambda x: x[0])[1] if timed else (frames[0] if frames else None)


def from_transcript(frames, transcript, note) -> List[Dict]:
    text, spans = _spoken(transcript)
    found = []
    for hit in scan_text(text):
        words = [w for a, b, w in spans if a < hit["end"] and hit["start"] < b]
        start, end = min(w["start"] for w in words), max(w["end"] for w in words)
        cand = {"kind": hit["kind"], "text": hit["text"], "rect": None, "start": start, "end": end,
                "frame": _nearest(frames, start), "source": "transcript"}
        if note:
            cand["note"] = note
        found.append(cand)
    return found
