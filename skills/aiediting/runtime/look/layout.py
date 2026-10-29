"""Layout guess: face filling the frame, screen + camera window, two tracks, vertical, screen only."""
from __future__ import annotations

from collections import Counter
from typing import Callable, Dict, List, Optional

from .errors import need
from .faces import yunet
from .window import find_circle

BIG_FACE = 0.03  # share of the frame a face takes when the camera is the whole picture


def _size(path):
    with need("PIL.Image", "раскладка кадра").open(path) as img:
        return img.size


def guess_frame(path, detector: Callable) -> Dict:
    """One frame -> {"frame" (str, JSON-safe), "kind", "face", "confidence"}."""
    w, h = _size(path)
    faces = detector(path)
    face = max(faces, key=lambda f: f["w"] * f["h"]) if faces else None
    if h > w * 1.1:
        return {"frame": str(path), "kind": "vertical", "face": face, "confidence": 0.9}
    circle = find_circle(path)
    if circle:
        rect = {k: circle[k] for k in ("x", "y", "w", "h")}
        return {"frame": str(path), "kind": "screen_face_window", "face": rect,
                "confidence": min(1.0, circle["score"])}
    if face and face["w"] * face["h"] >= BIG_FACE * w * h:
        return {"frame": str(path), "kind": "face_full", "face": face, "confidence": 0.85}
    if face:  # a small face without a round outline: a rectangular camera window
        grow = {"x": face["x"] - face["w"] // 2, "y": face["y"] - face["h"] // 2,
                "w": face["w"] * 2, "h": face["h"] * 2}
        return {"frame": str(path), "kind": "screen_face_window", "face": grow, "confidence": 0.6}
    return {"frame": str(path), "kind": "screen_only", "face": None, "confidence": 0.7}


def _median_rect(rects: List[Dict]) -> Optional[Dict]:
    rects = [r for r in rects if r]
    if not rects:
        return None
    mid = len(rects) // 2
    return {k: sorted(r[k] for r in rects)[mid] for k in ("x", "y", "w", "h")}


def _vote(shots: List[Dict]) -> Dict:
    kind, votes = Counter(s["kind"] for s in shots).most_common(1)[0]
    mine = [s for s in shots if s["kind"] == kind]
    conf = votes / len(shots) * sum(s["confidence"] for s in mine) / len(mine)
    return {"kind": kind, "face": _median_rect([s["face"] for s in mine]),
            "confidence": round(conf, 3), "frames": shots}


def detect_layout(frames, detector: Optional[Callable] = None) -> Dict:
    """LayoutGuess for one source (list of frames) or several (list of lists: separate tracks)."""
    detector = detector or yunet()
    groups = frames if frames and isinstance(frames[0], (list, tuple)) else [frames]
    per_source = [_vote([guess_frame(f, detector) for f in group]) for group in groups]
    if len(per_source) == 1:
        return per_source[0]
    kinds = {g["kind"] for g in per_source}
    if "face_full" in kinds and kinds & {"screen_only", "screen_face_window"}:
        face = next(g["face"] for g in per_source if g["kind"] == "face_full")
        conf = min(g["confidence"] for g in per_source)
        return {"kind": "separate_tracks", "face": face, "confidence": conf, "sources": per_source}
    best = max(per_source, key=lambda g: g["confidence"])
    return dict(best, sources=per_source)
