"""Where an element goes on the frame: a named spot, margins, the safe zone of vertical video."""
from __future__ import annotations

from typing import Dict, Tuple

from .design import load_design

SPOTS = ("bottom", "top", "center", "top-left", "top-right", "bottom-left", "bottom-right")


def margins(design, frame_size, margin: float) -> Dict[str, int]:
    """Pixels to keep free at each side; vertical frames also keep the platform's safe zone."""
    w, h = frame_size
    m = int(margin * h)
    sides = {"top": m, "bottom": m, "left": m, "right": m}
    if h > w:
        safe = load_design(design)["video"].get("safe_zone_vertical", {})
        sides["top"] = max(m, int(safe.get("top", 0) * h))
        sides["bottom"] = max(m, int(safe.get("bottom", 0) * h))
        sides["left"] = sides["right"] = max(m, int(safe.get("side", 0) * w))
    return sides


def place(design, frame_size, box: Tuple[int, int], where: str, margin: float) -> Tuple[int, int]:
    """Top-left corner for a box of `box` (w, h) at the spot `where`."""
    w, h = frame_size
    bw, bh = box
    m = margins(design, frame_size, margin)
    x = (w - bw) // 2
    if "left" in where:
        x = m["left"]
    elif "right" in where:
        x = w - m["right"] - bw
    y = (h - bh) // 2
    if where.startswith("top"):
        y = m["top"]
    elif where.startswith("bottom"):
        y = h - m["bottom"] - bh
    return x, y


def opposite_corner(face: Dict, frame_size) -> str:
    """The corner across the frame from a face window: graphics never sit on the face."""
    w, h = frame_size
    cx, cy = face["x"] + face["w"] / 2.0, face["y"] + face["h"] / 2.0
    return "{}-{}".format("top" if cy >= h / 2.0 else "bottom", "left" if cx >= w / 2.0 else "right")
