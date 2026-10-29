"""Where the face ends up in a finished 9:16 frame — so graphics on a vertical piece keep off it.

Mirrors the geometry of media.vertical: a stack puts the screen on top and the face crop below it,
«face» fills the frame with the face crop, «native» scales the whole picture to fit.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple


def _inside(rect: Dict, top: float, size: Tuple[int, int]) -> Optional[Dict]:
    x0, y0 = max(0.0, rect["x"]), max(float(top), rect["y"])
    x1, y1 = min(float(size[0]), rect["x"] + rect["w"]), min(float(size[1]), rect["y"] + rect["h"])
    if x1 <= x0 or y1 <= y0:
        return None
    return {"x": int(x0), "y": int(y0), "w": int(round(x1 - x0)), "h": int(round(y1 - y0))}


def face_in_vertical(layout: Optional[Dict], frame: Tuple[int, int], size: Tuple[int, int]) -> Optional[Dict]:
    """The face rect of a 9:16 piece in pixels of the finished `size` frame; None when no face is shown.

    layout: the piece's Layout (media.vertical); frame: the source picture as shown.
    """
    from ..media.vertical import _screen_height, crop_box

    face, kind = (layout or {}).get("face"), (layout or {}).get("kind")
    if not face:
        return None
    w, h = size
    if kind == "native":
        k = min(w / float(frame[0]), h / float(frame[1]))
        ox, oy = (w - frame[0] * k) / 2.0, (h - frame[1] * k) / 2.0
        return _inside({"x": ox + face["x"] * k, "y": oy + face["y"] * k, "w": face["w"] * k,
                        "h": face["h"] * k}, 0, size)
    if kind not in ("stack", "face"):
        return None
    top = 0 if kind == "face" else _screen_height(layout.get("screen") or {"w": frame[0], "h": frame[1]}, size)
    box = crop_box(face, w / float(h - top), frame, layout.get("room", 1.0))
    kx, ky = w / float(box["w"]), (h - top) / float(box["h"])
    return _inside({"x": (face["x"] - box["x"]) * kx, "y": top + (face["y"] - box["y"]) * ky,
                    "w": face["w"] * kx, "h": face["h"] * ky}, top, size)
