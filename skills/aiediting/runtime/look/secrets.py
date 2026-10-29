"""Candidates for blurring: secret-looking text on frames (OCR) and in the transcript.

Nothing here closes anything: the list goes to a human, who ticks what to blur and adds their own.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from .frames import frame_time
from .ocr import ocr_backend, read_lines
from .patterns import scan_text
from .spoken import from_transcript

NO_OCR = "найдено без распознавания текста на кадрах — только по расшифровке; экран проверьте глазами"


def _part(rect: Dict, line: str, a: int, b: int) -> Dict:
    """The share of a line's box that characters a..b take (close enough for a blur box)."""
    n = max(1, len(line))
    x0 = rect["x"] + rect["w"] * a // n
    x1 = rect["x"] + rect["w"] * b // n
    pad = rect["h"] // 4
    return {"x": max(0, x0 - pad), "y": rect["y"], "w": x1 - x0 + 2 * pad, "h": rect["h"]}


def _from_frames(frames: List[Path], backend: str) -> List[Dict]:
    found: Dict[tuple, Dict] = {}
    for frame, lines in zip(frames, read_lines(frames, backend)):
        t = frame_time(frame)
        for line in lines:
            for hit in scan_text(line["text"]):
                key = (hit["kind"], hit["text"])
                if key in found:  # same text on a later frame: widen the time, keep the first box
                    found[key]["end"] = t if t is not None else found[key]["end"]
                    continue
                found[key] = {"kind": hit["kind"], "text": hit["text"], "start": t, "end": t,
                              "rect": _part(line["rect"], line["text"], hit["start"], hit["end"]),
                              "frame": frame, "source": "ocr"}
    return list(found.values())


def find_secrets(frames, transcript, ocr="auto") -> List[Dict]:
    """Candidate = {"kind","text","rect","start","end","frame","source"[, "note"]}.

    ocr: "auto" (best available), "vision", "tesseract", or False to read the transcript only.
    """
    frames = [Path(f) for f in frames]
    backend = (ocr_backend() if ocr == "auto" else ocr) if ocr else None
    found = _from_frames(frames, backend) if backend and frames else []
    return found + from_transcript(frames, transcript, None if backend else NO_OCR)
